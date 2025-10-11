"""
Unit tests for WorkspaceManager.
"""

import pytest
from pathlib import Path
from src.tools.workspace_manager import WorkspaceManager


class TestWorkspaceManager:
    """Test WorkspaceManager functionality."""

    def test_workspace_creation(self):
        """Test workspace is created."""
        with WorkspaceManager() as workspace:
            assert workspace.base_path.exists()
            assert workspace.base_path.is_dir()
            assert str(workspace.base_path).startswith("/tmp/devmatrix-workspace-")

    def test_workspace_cleanup(self):
        """Test workspace cleanup on exit."""
        workspace = WorkspaceManager()
        workspace.create()
        workspace_path = workspace.base_path

        assert workspace_path.exists()

        workspace.cleanup()
        assert not workspace_path.exists()

    def test_context_manager_auto_cleanup(self):
        """Test context manager cleans up automatically."""
        workspace_path = None

        with WorkspaceManager() as workspace:
            workspace_path = workspace.base_path
            assert workspace_path.exists()

        assert not workspace_path.exists()

    def test_context_manager_no_cleanup(self):
        """Test context manager without auto-cleanup."""
        workspace_path = None

        with WorkspaceManager(auto_cleanup=False) as workspace:
            workspace_path = workspace.base_path
            assert workspace_path.exists()

        assert workspace_path.exists()
        # Manual cleanup
        WorkspaceManager(workspace_id=workspace_path.name.replace("devmatrix-workspace-", "")).cleanup()

    def test_write_and_read_file(self):
        """Test writing and reading files."""
        with WorkspaceManager() as workspace:
            content = "Hello, World!"
            file_path = workspace.write_file("test.txt", content)

            assert file_path.exists()
            assert workspace.read_file("test.txt") == content

    def test_file_exists(self):
        """Test file exists check."""
        with WorkspaceManager() as workspace:
            assert not workspace.file_exists("nonexistent.txt")

            workspace.write_file("exists.txt", "content")
            assert workspace.file_exists("exists.txt")

    def test_dir_exists(self):
        """Test directory exists check."""
        with WorkspaceManager() as workspace:
            assert not workspace.dir_exists("nonexistent_dir")

            workspace.get_path("test_dir").mkdir()
            assert workspace.dir_exists("test_dir")

    def test_list_files(self):
        """Test listing files in workspace."""
        with WorkspaceManager() as workspace:
            # Create multiple files
            workspace.write_file("file1.txt", "content1")
            workspace.write_file("file2.txt", "content2")
            workspace.write_file("subdir/file3.txt", "content3")

            # List all txt files in root
            files = workspace.list_files("", "*.txt")
            assert len(files) == 2
            assert Path("file1.txt") in files
            assert Path("file2.txt") in files

    def test_list_dirs(self):
        """Test listing directories."""
        with WorkspaceManager() as workspace:
            workspace.get_path("dir1").mkdir()
            workspace.get_path("dir2").mkdir()
            workspace.get_path("dir1/subdir").mkdir(parents=True)

            dirs = workspace.list_dirs()
            assert len(dirs) == 2
            assert Path("dir1") in dirs
            assert Path("dir2") in dirs

    def test_delete_file(self):
        """Test file deletion."""
        with WorkspaceManager() as workspace:
            workspace.write_file("to_delete.txt", "content")
            assert workspace.file_exists("to_delete.txt")

            deleted = workspace.delete_file("to_delete.txt")
            assert deleted is True
            assert not workspace.file_exists("to_delete.txt")

    def test_delete_nonexistent_file(self):
        """Test deleting non-existent file returns False."""
        with WorkspaceManager() as workspace:
            deleted = workspace.delete_file("nonexistent.txt")
            assert deleted is False

    def test_delete_dir(self):
        """Test directory deletion."""
        with WorkspaceManager() as workspace:
            workspace.get_path("to_delete_dir").mkdir()
            workspace.write_file("to_delete_dir/file.txt", "content")

            assert workspace.dir_exists("to_delete_dir")

            deleted = workspace.delete_dir("to_delete_dir")
            assert deleted is True
            assert not workspace.dir_exists("to_delete_dir")

    def test_nested_directories(self):
        """Test creating files in nested directories."""
        with WorkspaceManager() as workspace:
            content = "nested content"
            file_path = workspace.write_file("a/b/c/nested.txt", content)

            assert file_path.exists()
            assert workspace.read_file("a/b/c/nested.txt") == content

    def test_get_size(self):
        """Test workspace size calculation."""
        with WorkspaceManager() as workspace:
            initial_size = workspace.get_size()
            assert initial_size == 0

            workspace.write_file("file1.txt", "a" * 100)
            workspace.write_file("file2.txt", "b" * 200)

            size = workspace.get_size()
            assert size == 300

    def test_path_traversal_protection(self):
        """Test protection against path traversal."""
        with WorkspaceManager() as workspace:
            # Should raise ValueError for paths outside workspace
            with pytest.raises(ValueError):
                workspace.get_path("../../../etc/passwd")

    def test_custom_workspace_id(self):
        """Test creating workspace with custom ID."""
        custom_id = "test_custom_id"
        workspace = WorkspaceManager(workspace_id=custom_id, auto_cleanup=False)
        workspace.create()

        assert workspace.workspace_id == custom_id
        assert str(workspace.base_path).endswith(f"devmatrix-workspace-{custom_id}")

        workspace.cleanup()

    def test_unicode_content(self):
        """Test handling Unicode content."""
        with WorkspaceManager() as workspace:
            content = "Hello 世界 🚀 émojis"
            workspace.write_file("unicode.txt", content)

            read_content = workspace.read_file("unicode.txt")
            assert read_content == content

    def test_empty_file(self):
        """Test creating empty file."""
        with WorkspaceManager() as workspace:
            workspace.write_file("empty.txt", "")

            content = workspace.read_file("empty.txt")
            assert content == ""
            assert workspace.file_exists("empty.txt")

    def test_get_path_creates_workspace(self):
        """Test get_path creates workspace if not created."""
        workspace = WorkspaceManager(auto_cleanup=False)
        # Don't call create() explicitly
        assert workspace._created is False

        # get_path should create workspace automatically
        path = workspace.get_path("test.txt")
        assert workspace._created is True
        assert workspace.base_path.exists()

        # Cleanup
        workspace.cleanup()

    def test_file_exists_with_invalid_path(self):
        """Test file_exists returns False for invalid paths."""
        with WorkspaceManager() as workspace:
            # Path traversal should return False
            exists = workspace.file_exists("../../../etc/passwd")
            assert exists is False

    def test_dir_exists_with_invalid_path(self):
        """Test dir_exists returns False for invalid paths."""
        with WorkspaceManager() as workspace:
            # Path traversal should return False
            exists = workspace.dir_exists("../../../etc")
            assert exists is False

    def test_list_files_empty_directory(self):
        """Test listing files in empty directory."""
        with WorkspaceManager() as workspace:
            workspace.get_path("empty_dir").mkdir()
            files = workspace.list_files("empty_dir")
            assert files == []

    def test_list_dirs_empty_directory(self):
        """Test listing dirs in empty directory."""
        with WorkspaceManager() as workspace:
            workspace.get_path("empty_dir").mkdir()
            dirs = workspace.list_dirs("empty_dir")
            assert dirs == []

    def test_delete_file_exception_handling(self):
        """Test delete_file handles exceptions."""
        with WorkspaceManager() as workspace:
            # Try to delete with invalid path
            result = workspace.delete_file("../../../etc/passwd")
            assert result is False

    def test_delete_dir_exception_handling(self):
        """Test delete_dir handles exceptions."""
        with WorkspaceManager() as workspace:
            # Try to delete with invalid path
            result = workspace.delete_dir("../../../etc")
            assert result is False

    def test_cleanup_exception_handling(self, monkeypatch, capsys):
        """Test cleanup handles exceptions and prints error."""
        workspace = WorkspaceManager(auto_cleanup=False)
        workspace.create()

        # Mock rmtree to raise exception
        import shutil
        original_rmtree = shutil.rmtree
        def mock_rmtree(path):
            raise PermissionError("Cannot delete")

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

        result = workspace.cleanup()
        assert result is False

        # Check error message was printed
        captured = capsys.readouterr()
        assert "Error cleaning up workspace" in captured.out

        # Restore and cleanup properly
        monkeypatch.setattr(shutil, "rmtree", original_rmtree)
        workspace.cleanup()

    def test_get_size_empty_workspace(self):
        """Test get_size returns 0 for non-existent workspace."""
        workspace = WorkspaceManager(auto_cleanup=False)
        # Don't create workspace
        size = workspace.get_size()
        assert size == 0

    def test_string_representation(self):
        """Test __str__ method."""
        workspace = WorkspaceManager(workspace_id="test123", auto_cleanup=False)
        workspace.create()

        str_repr = str(workspace)
        assert "test123" in str_repr
        assert "devmatrix-workspace-test123" in str_repr

        workspace.cleanup()

    def test_list_files_nonexistent_path(self):
        """Test list_files with nonexistent path returns empty list."""
        with WorkspaceManager() as workspace:
            # This should return empty list (covers line 148)
            files = workspace.list_files("nonexistent_path")
            assert files == []

    def test_list_dirs_nonexistent_path(self):
        """Test list_dirs with nonexistent path returns empty list."""
        with WorkspaceManager() as workspace:
            # This should return empty list (covers line 171)
            dirs = workspace.list_dirs("nonexistent_path")
            assert dirs == []

    def test_delete_dir_with_permission_error(self, monkeypatch):
        """Test delete_dir handles rmtree exception."""
        workspace = WorkspaceManager(auto_cleanup=False)
        workspace.create()

        # Create a directory
        test_dir = workspace.get_path("test_dir")
        test_dir.mkdir()

        # Mock rmtree to raise exception
        import shutil
        original_rmtree = shutil.rmtree
        def mock_rmtree(path):
            raise PermissionError("Cannot delete directory")

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

        # Should return False on exception (covers line 215)
        result = workspace.delete_dir("test_dir")
        assert result is False

        # Cleanup
        monkeypatch.setattr(shutil, "rmtree", original_rmtree)
        workspace.cleanup()

    def test_cleanup_nonexistent_workspace(self):
        """Test cleanup returns False when workspace doesn't exist."""
        workspace = WorkspaceManager(auto_cleanup=False)
        # Don't create workspace

        # Should return False (covers line 231)
        result = workspace.cleanup()
        assert result is False
