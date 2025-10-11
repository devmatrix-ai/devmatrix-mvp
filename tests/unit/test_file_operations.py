"""
Unit tests for FileOperations.
"""

import pytest
from pathlib import Path
from src.tools.file_operations import FileOperations


class TestFileOperations:
    """Test FileOperations functionality."""

    @pytest.fixture
    def temp_base(self, tmp_path):
        """Create temporary base directory."""
        return tmp_path / "test_base"

    def test_initialization_creates_base_path(self, temp_base):
        """Test base path is created on initialization."""
        file_ops = FileOperations(str(temp_base))
        assert temp_base.exists()
        assert temp_base.is_dir()

    def test_write_and_read_file(self, temp_base):
        """Test writing and reading files."""
        file_ops = FileOperations(str(temp_base))
        content = "Hello, World!"
        file_ops.write_file("test.txt", content)

        read_content = file_ops.read_file("test.txt")
        assert read_content == content

    def test_write_creates_nested_directories(self, temp_base):
        """Test writing files creates parent directories."""
        file_ops = FileOperations(str(temp_base))
        content = "nested content"
        file_ops.write_file("a/b/c/nested.txt", content)

        assert file_ops.file_exists("a/b/c/nested.txt")
        assert file_ops.read_file("a/b/c/nested.txt") == content

    def test_append_file(self, temp_base):
        """Test appending to files."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("test.txt", "Hello")
        file_ops.append_file("test.txt", " World")

        content = file_ops.read_file("test.txt")
        assert content == "Hello World"

    def test_delete_file(self, temp_base):
        """Test file deletion."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("to_delete.txt", "content")
        assert file_ops.file_exists("to_delete.txt")

        deleted = file_ops.delete_file("to_delete.txt")
        assert deleted is True
        assert not file_ops.file_exists("to_delete.txt")

    def test_delete_nonexistent_file(self, temp_base):
        """Test deleting non-existent file returns False."""
        file_ops = FileOperations(str(temp_base))
        deleted = file_ops.delete_file("nonexistent.txt")
        assert deleted is False

    def test_file_exists(self, temp_base):
        """Test file existence check."""
        file_ops = FileOperations(str(temp_base))
        assert not file_ops.file_exists("nonexistent.txt")

        file_ops.write_file("exists.txt", "content")
        assert file_ops.file_exists("exists.txt")

    def test_list_files(self, temp_base):
        """Test listing files."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("file1.txt", "content1")
        file_ops.write_file("file2.txt", "content2")
        file_ops.write_file("file3.py", "content3")
        file_ops.write_file("subdir/file4.txt", "content4")

        # List all txt files in root
        files = file_ops.list_files("", "*.txt")
        assert len(files) == 2
        assert "file1.txt" in files
        assert "file2.txt" in files

        # List all files recursively
        all_files = file_ops.list_files("", "*", recursive=True)
        assert len(all_files) == 4

    def test_list_dirs(self, temp_base):
        """Test listing directories."""
        file_ops = FileOperations(str(temp_base))
        file_ops.create_dir("dir1")
        file_ops.create_dir("dir2")
        file_ops.create_dir("dir1/subdir")

        dirs = file_ops.list_dirs()
        assert len(dirs) == 2
        assert "dir1" in dirs
        assert "dir2" in dirs

    def test_create_dir(self, temp_base):
        """Test directory creation."""
        file_ops = FileOperations(str(temp_base))
        dir_path = file_ops.create_dir("test_dir")

        assert dir_path.exists()
        assert dir_path.is_dir()

    def test_get_file_info(self, temp_base):
        """Test file metadata retrieval."""
        file_ops = FileOperations(str(temp_base))
        content = "test content"
        file_ops.write_file("test.txt", content)

        info = file_ops.get_file_info("test.txt")
        assert info["name"] == "test.txt"
        assert info["size"] == len(content)
        assert info["is_file"] is True
        assert info["is_dir"] is False
        assert info["extension"] == ".txt"

    def test_get_file_hash(self, temp_base):
        """Test file hashing."""
        file_ops = FileOperations(str(temp_base))
        content = "test content"
        file_ops.write_file("test.txt", content)

        # SHA256 hash
        hash_sha256 = file_ops.get_file_hash("test.txt", "sha256")
        assert len(hash_sha256) == 64  # SHA256 produces 64 hex chars

        # MD5 hash
        hash_md5 = file_ops.get_file_hash("test.txt", "md5")
        assert len(hash_md5) == 32  # MD5 produces 32 hex chars

    def test_copy_file(self, temp_base):
        """Test file copying."""
        file_ops = FileOperations(str(temp_base))
        content = "original content"
        file_ops.write_file("original.txt", content)

        file_ops.copy_file("original.txt", "copy.txt")

        assert file_ops.file_exists("original.txt")
        assert file_ops.file_exists("copy.txt")
        assert file_ops.read_file("copy.txt") == content

    def test_move_file(self, temp_base):
        """Test file moving."""
        file_ops = FileOperations(str(temp_base))
        content = "original content"
        file_ops.write_file("original.txt", content)

        file_ops.move_file("original.txt", "moved.txt")

        assert not file_ops.file_exists("original.txt")
        assert file_ops.file_exists("moved.txt")
        assert file_ops.read_file("moved.txt") == content

    def test_get_tree(self, temp_base):
        """Test directory tree structure."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("file1.txt", "content1")
        file_ops.write_file("dir1/file2.txt", "content2")
        file_ops.write_file("dir1/dir2/file3.txt", "content3")

        tree = file_ops.get_tree()
        assert tree["type"] == "directory"
        assert len(tree["children"]) == 2  # file1.txt and dir1

    def test_path_traversal_protection(self, temp_base):
        """Test protection against path traversal."""
        file_ops = FileOperations(str(temp_base))

        # Should raise ValueError for paths outside base
        with pytest.raises(ValueError):
            file_ops.read_file("../../../etc/passwd")

        with pytest.raises(ValueError):
            file_ops.write_file("../../../tmp/malicious.txt", "bad")

    def test_unicode_content(self, temp_base):
        """Test handling Unicode content."""
        file_ops = FileOperations(str(temp_base))
        content = "Hello 世界 🚀 émojis"
        file_ops.write_file("unicode.txt", content)

        read_content = file_ops.read_file("unicode.txt")
        assert read_content == content

    def test_empty_file(self, temp_base):
        """Test creating empty file."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("empty.txt", "")

        content = file_ops.read_file("empty.txt")
        assert content == ""
        assert file_ops.file_exists("empty.txt")

    def test_large_file(self, temp_base):
        """Test handling large files."""
        file_ops = FileOperations(str(temp_base))
        # Create 1MB file
        large_content = "a" * (1024 * 1024)
        file_ops.write_file("large.txt", large_content)

        info = file_ops.get_file_info("large.txt")
        assert info["size"] == 1024 * 1024

    def test_special_characters_in_filename(self, temp_base):
        """Test files with special characters in names."""
        file_ops = FileOperations(str(temp_base))
        content = "special content"
        file_ops.write_file("file with spaces.txt", content)

        assert file_ops.file_exists("file with spaces.txt")
        assert file_ops.read_file("file with spaces.txt") == content

    def test_read_nonexistent_file(self, temp_base):
        """Test reading non-existent file raises error."""
        file_ops = FileOperations(str(temp_base))

        with pytest.raises(FileNotFoundError):
            file_ops.read_file("nonexistent.txt")

    def test_get_info_nonexistent_file(self, temp_base):
        """Test getting info for non-existent file raises error."""
        file_ops = FileOperations(str(temp_base))

        with pytest.raises(FileNotFoundError):
            file_ops.get_file_info("nonexistent.txt")

    def test_copy_to_nested_destination(self, temp_base):
        """Test copying to nested directory creates parents."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("source.txt", "content")

        file_ops.copy_file("source.txt", "a/b/c/destination.txt")

        assert file_ops.file_exists("a/b/c/destination.txt")
        assert file_ops.read_file("a/b/c/destination.txt") == "content"

    def test_different_encodings(self, temp_base):
        """Test reading/writing with different encodings."""
        file_ops = FileOperations(str(temp_base))
        content = "Special chars: ñ, ü, é"

        # Write with UTF-8
        file_ops.write_file("utf8.txt", content, encoding="utf-8")
        read_utf8 = file_ops.read_file("utf8.txt", encoding="utf-8")
        assert read_utf8 == content

    def test_tree_max_depth(self, temp_base):
        """Test tree structure respects max depth."""
        file_ops = FileOperations(str(temp_base))
        file_ops.write_file("a/b/c/d/e/deep.txt", "content")

        tree = file_ops.get_tree(max_depth=2)
        # Should truncate at depth 2
        assert tree["type"] == "directory"

    def test_delete_file_with_permission_error(self, temp_base):
        """Test delete_file handles exceptions gracefully."""
        file_ops = FileOperations(str(temp_base))

        # Try to delete with invalid path that causes exception
        result = file_ops.delete_file("../../../etc/passwd")
        assert result is False

    def test_file_exists_with_invalid_path(self, temp_base):
        """Test file_exists returns False for invalid paths."""
        file_ops = FileOperations(str(temp_base))

        # Path traversal should return False
        exists = file_ops.file_exists("../../../etc/passwd")
        assert exists is False

    def test_list_files_nonexistent_directory(self, temp_base):
        """Test listing files in non-existent directory returns empty."""
        file_ops = FileOperations(str(temp_base))

        files = file_ops.list_files("nonexistent_dir", "*.txt")
        assert files == []

    def test_list_dirs_nonexistent_directory(self, temp_base):
        """Test listing directories in non-existent directory returns empty."""
        file_ops = FileOperations(str(temp_base))

        dirs = file_ops.list_dirs("nonexistent_dir")
        assert dirs == []

    def test_tree_with_permission_error(self, temp_base, monkeypatch):
        """Test tree handles PermissionError gracefully."""
        file_ops = FileOperations(str(temp_base))
        file_ops.create_dir("restricted")

        # Mock iterdir to raise PermissionError
        original_iterdir = Path.iterdir
        def mock_iterdir(self):
            if "restricted" in str(self):
                raise PermissionError("Access denied")
            return original_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", mock_iterdir)

        tree = file_ops.get_tree()
        # Should handle PermissionError and continue
        assert tree["type"] == "directory"
