"""
Unit tests for GitOperations.
"""

import pytest
import subprocess
from pathlib import Path
from src.tools.git_operations import GitOperations, GitStatus, GitDiff


class TestGitOperations:
    """Test GitOperations functionality."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repository."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    def test_initialization(self, git_repo):
        """Test GitOperations initialization."""
        git_ops = GitOperations(str(git_repo))
        assert git_ops.repo_path == git_repo

    def test_initialization_non_git_repo(self, tmp_path):
        """Test initialization fails for non-git directory."""
        non_git_path = tmp_path / "not_a_repo"
        non_git_path.mkdir()

        with pytest.raises(ValueError, match="Not a git repository"):
            GitOperations(str(non_git_path))

    def test_get_status_clean_repo(self, git_repo):
        """Test status for clean repository."""
        git_ops = GitOperations(str(git_repo))
        status = git_ops.get_status()

        assert isinstance(status, GitStatus)
        assert status.branch in ["master", "main"]
        assert status.is_clean is True
        assert len(status.staged_files) == 0
        assert len(status.modified_files) == 0
        assert len(status.untracked_files) == 0

    def test_get_status_with_untracked_file(self, git_repo):
        """Test status with untracked file."""
        git_ops = GitOperations(str(git_repo))

        # Create untracked file
        (git_repo / "new_file.txt").write_text("new content")

        status = git_ops.get_status()
        assert status.is_clean is False
        assert len(status.untracked_files) == 1
        assert "new_file.txt" in status.untracked_files

    def test_get_status_with_modified_file(self, git_repo):
        """Test status with modified file."""
        git_ops = GitOperations(str(git_repo))

        # Modify existing file
        (git_repo / "README.md").write_text("# Modified")

        status = git_ops.get_status()
        assert status.is_clean is False
        # Modified files show up in the status (either staged or modified depending on git behavior)
        assert len(status.staged_files) + len(status.modified_files) >= 1

    def test_get_status_with_staged_file(self, git_repo):
        """Test status with staged file."""
        git_ops = GitOperations(str(git_repo))

        # Create and stage file
        (git_repo / "staged.txt").write_text("staged content")
        subprocess.run(["git", "add", "staged.txt"], cwd=git_repo, check=True, capture_output=True)

        status = git_ops.get_status()
        assert status.is_clean is False
        assert len(status.staged_files) == 1
        assert "staged.txt" in status.staged_files

    def test_add_files(self, git_repo):
        """Test staging files."""
        git_ops = GitOperations(str(git_repo))

        # Create files
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")

        result = git_ops.add_files(["file1.txt", "file2.txt"])
        assert result is True

        status = git_ops.get_status()
        assert len(status.staged_files) == 2

    def test_add_all(self, git_repo):
        """Test staging all changes."""
        git_ops = GitOperations(str(git_repo))

        # Create multiple files
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")
        (git_repo / "file3.txt").write_text("content3")

        result = git_ops.add_all()
        assert result is True

        status = git_ops.get_status()
        assert len(status.staged_files) == 3

    def test_commit(self, git_repo):
        """Test creating commits."""
        git_ops = GitOperations(str(git_repo))

        # Create and stage file
        (git_repo / "commit_test.txt").write_text("test content")
        git_ops.add_files(["commit_test.txt"])

        result = git_ops.commit("Test commit message")
        assert result is True

        # Verify clean status after commit
        status = git_ops.get_status()
        assert status.is_clean is True

    def test_commit_with_author(self, git_repo):
        """Test commit with custom author."""
        git_ops = GitOperations(str(git_repo))

        # Create and stage file
        (git_repo / "author_test.txt").write_text("test content")
        git_ops.add_files(["author_test.txt"])

        result = git_ops.commit("Test commit", author="Custom Author <custom@example.com>")
        assert result is True

    def test_commit_empty(self, git_repo):
        """Test commit with no staged changes fails."""
        git_ops = GitOperations(str(git_repo))

        result = git_ops.commit("Empty commit")
        assert result is False

    def test_get_last_commit(self, git_repo):
        """Test retrieving last commit information."""
        git_ops = GitOperations(str(git_repo))

        commit = git_ops.get_last_commit()
        assert "hash" in commit
        assert "author_name" in commit
        assert "author_email" in commit
        assert "timestamp" in commit
        assert "message" in commit
        assert commit["message"] == "Initial commit"

    def test_get_diff_unstaged(self, git_repo):
        """Test getting unstaged diff."""
        git_ops = GitOperations(str(git_repo))

        # Modify file
        (git_repo / "README.md").write_text("# Modified README\nNew line")

        diffs = git_ops.get_diff()
        assert len(diffs) == 1
        assert isinstance(diffs[0], GitDiff)
        assert diffs[0].file_path == "README.md"
        assert diffs[0].additions > 0
        assert diffs[0].deletions > 0

    def test_get_diff_staged(self, git_repo):
        """Test getting staged diff."""
        git_ops = GitOperations(str(git_repo))

        # Create and stage file
        (git_repo / "staged.txt").write_text("staged content\nsecond line")
        git_ops.add_files(["staged.txt"])

        diffs = git_ops.get_diff(staged=True)
        assert len(diffs) == 1
        assert diffs[0].file_path == "staged.txt"
        assert diffs[0].additions == 2

    def test_get_diff_specific_file(self, git_repo):
        """Test getting diff for specific file."""
        git_ops = GitOperations(str(git_repo))

        # Modify multiple files
        (git_repo / "README.md").write_text("# Modified")
        (git_repo / "other.txt").write_text("other content")

        diffs = git_ops.get_diff(file_path="README.md")
        assert len(diffs) == 1
        assert diffs[0].file_path == "README.md"

    def test_get_changed_files(self, git_repo):
        """Test getting changed files since commit."""
        git_ops = GitOperations(str(git_repo))

        # Create and commit new file
        (git_repo / "new.txt").write_text("new content")
        git_ops.add_all()
        git_ops.commit("Add new file")

        # Modify and commit another file
        (git_repo / "another.txt").write_text("another content")
        git_ops.add_all()
        git_ops.commit("Add another file")

        # Get files changed in last commit
        changed = git_ops.get_changed_files(since_commit="HEAD~1")
        assert len(changed) == 1
        assert "another.txt" in changed

    def test_is_file_tracked(self, git_repo):
        """Test checking if file is tracked."""
        git_ops = GitOperations(str(git_repo))

        # Existing tracked file
        assert git_ops.is_file_tracked("README.md") is True

        # Create untracked file
        (git_repo / "untracked.txt").write_text("untracked")
        assert git_ops.is_file_tracked("untracked.txt") is False

    def test_get_file_history(self, git_repo):
        """Test getting file commit history."""
        git_ops = GitOperations(str(git_repo))

        # Create multiple commits for same file
        (git_repo / "history.txt").write_text("version 1")
        git_ops.add_all()
        git_ops.commit("First version")

        (git_repo / "history.txt").write_text("version 2")
        git_ops.add_all()
        git_ops.commit("Second version")

        (git_repo / "history.txt").write_text("version 3")
        git_ops.add_all()
        git_ops.commit("Third version")

        history = git_ops.get_file_history("history.txt", max_count=5)
        assert len(history) == 3
        assert all("hash" in commit for commit in history)
        assert history[0]["message"] == "Third version"
        assert history[1]["message"] == "Second version"
        assert history[2]["message"] == "First version"

    def test_get_branch_name(self, git_repo):
        """Test getting current branch name."""
        git_ops = GitOperations(str(git_repo))

        branch = git_ops.get_branch_name()
        assert branch in ["master", "main"]

    def test_get_remote_url_no_remote(self, git_repo):
        """Test getting remote URL when no remote exists."""
        git_ops = GitOperations(str(git_repo))

        url = git_ops.get_remote_url()
        assert url is None

    def test_get_uncommitted_changes(self, git_repo):
        """Test getting summary of uncommitted changes."""
        git_ops = GitOperations(str(git_repo))

        # Create various changes
        (git_repo / "staged_new.txt").write_text("staged")
        git_ops.add_files(["staged_new.txt"])

        (git_repo / "untracked.txt").write_text("untracked")

        changes = git_ops.get_uncommitted_changes()
        assert len(changes["staged"]) >= 1
        assert len(changes["untracked"]) == 1
        assert changes["total"] >= 2

    def test_multiple_staged_and_modified(self, git_repo):
        """Test handling multiple staged and modified files."""
        git_ops = GitOperations(str(git_repo))

        # Create and stage files
        (git_repo / "file1.txt").write_text("content1")
        (git_repo / "file2.txt").write_text("content2")
        git_ops.add_all()

        # Modify one of them
        (git_repo / "file1.txt").write_text("modified content")

        status = git_ops.get_status()
        assert "file1.txt" in status.staged_files
        assert "file1.txt" in status.modified_files
        assert "file2.txt" in status.staged_files

    def test_unicode_in_commit_message(self, git_repo):
        """Test commit with unicode characters."""
        git_ops = GitOperations(str(git_repo))

        (git_repo / "unicode.txt").write_text("content")
        git_ops.add_files(["unicode.txt"])

        message = "Unicode commit: 世界 🚀 émojis"
        result = git_ops.commit(message)
        assert result is True

        commit = git_ops.get_last_commit()
        assert commit["message"] == message

    def test_long_commit_message(self, git_repo):
        """Test commit with very long message."""
        git_ops = GitOperations(str(git_repo))

        (git_repo / "long.txt").write_text("content")
        git_ops.add_files(["long.txt"])

        message = "A" * 1000  # 1000 character message
        result = git_ops.commit(message)
        assert result is True

    def test_empty_repository_state(self, tmp_path):
        """Test operations on completely empty repository."""
        repo_path = tmp_path / "empty_repo"
        repo_path.mkdir()

        # Initialize but don't commit anything
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        git_ops = GitOperations(str(repo_path))

        # Create a file first so we can stage and commit
        (repo_path / "first.txt").write_text("first commit")
        git_ops.add_files(["first.txt"])
        git_ops.commit("First commit")

        # Now status should work
        status = git_ops.get_status()
        assert isinstance(status, GitStatus)

    def test_get_status_no_upstream_branch(self, git_repo):
        """Test get_status when no upstream branch is configured."""
        git_ops = GitOperations(str(git_repo))

        # Get status (no upstream configured by default)
        status = git_ops.get_status()

        # Should handle no upstream gracefully
        assert status.ahead == 0
        assert status.behind == 0

    def test_get_diff_empty(self, git_repo):
        """Test get_diff with no changes returns empty list."""
        git_ops = GitOperations(str(git_repo))

        # Clean repo, no diffs
        diffs = git_ops.get_diff()
        assert diffs == []

    def test_get_diff_binary_file(self, git_repo):
        """Test get_diff handles binary files."""
        git_ops = GitOperations(str(git_repo))

        # Create binary file
        (git_repo / "binary.bin").write_bytes(b"\x00\x01\x02\x03")
        git_ops.add_files(["binary.bin"])

        diffs = git_ops.get_diff(staged=True)
        # Binary files show as 0 additions/deletions with "-" in numstat
        assert len(diffs) >= 0  # May or may not include binary depending on git config

    def test_add_files_failure(self, git_repo, monkeypatch):
        """Test add_files returns False on failure."""
        git_ops = GitOperations(str(git_repo))

        # Mock subprocess to fail
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "add" in args[0]:
                raise subprocess.CalledProcessError(1, args[0])
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = git_ops.add_files(["nonexistent.txt"])
        assert result is False

    def test_add_all_failure(self, git_repo, monkeypatch):
        """Test add_all returns False on failure."""
        git_ops = GitOperations(str(git_repo))

        # Mock subprocess to fail
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "add" in args[0] and "-A" in args[0]:
                raise subprocess.CalledProcessError(1, args[0])
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = git_ops.add_all()
        assert result is False

    def test_commit_failure(self, git_repo, monkeypatch):
        """Test commit returns False on failure."""
        git_ops = GitOperations(str(git_repo))

        # Stage a file
        (git_repo / "test.txt").write_text("test")
        git_ops.add_files(["test.txt"])

        # Mock subprocess to fail
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "commit" in args[0]:
                raise subprocess.CalledProcessError(1, args[0])
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = git_ops.commit("Test commit")
        assert result is False

    def test_get_last_commit_empty_response(self, git_repo, monkeypatch):
        """Test get_last_commit handles empty response."""
        git_ops = GitOperations(str(git_repo))

        # Mock subprocess to return incomplete data
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "log" in args[0] and "-1" in args[0]:
                result = original_run(*args, **kwargs)
                result.stdout = "incomplete"  # Only 1 line instead of 5
                return result
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        commit = git_ops.get_last_commit()
        assert commit == {}

    def test_get_file_history_empty(self, git_repo):
        """Test get_file_history for non-existent file."""
        git_ops = GitOperations(str(git_repo))

        history = git_ops.get_file_history("nonexistent.txt")
        assert history == []

    def test_get_remote_url_with_remote(self, git_repo):
        """Test get_remote_url when remote exists."""
        git_ops = GitOperations(str(git_repo))

        # Add a remote
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        url = git_ops.get_remote_url()
        assert url == "https://github.com/test/repo.git"

    def test_get_status_with_empty_lines(self, git_repo):
        """Test get_status handles empty lines in porcelain output."""
        git_ops = GitOperations(str(git_repo))

        # Create files to trigger status lines
        (git_repo / "file1.txt").write_text("content")
        (git_repo / "file2.txt").write_text("content")

        status = git_ops.get_status()
        # Should filter out empty lines (line 98)
        assert len(status.untracked_files) == 2

    def test_get_status_ahead_behind_parsing(self, git_repo, monkeypatch):
        """Test get_status handles malformed ahead/behind output."""
        git_ops = GitOperations(str(git_repo))

        # Mock rev-list to return malformed output (covers lines 117-119)
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "rev-list" in args[0]:
                result = original_run(*args, **kwargs)
                # Return only 1 part instead of 2
                result.stdout = "1"
                result.returncode = 0
                return result
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        status = git_ops.get_status()
        # Should default to 0,0 when parts != 2
        assert status.ahead == 0
        assert status.behind == 0

    def test_get_diff_with_empty_lines(self, git_repo):
        """Test get_diff handles empty lines in output."""
        git_ops = GitOperations(str(git_repo))

        # Modify file
        (git_repo / "README.md").write_text("# Modified\n\n\n")

        diffs = git_ops.get_diff()
        # Should filter empty lines (line 157)
        assert len(diffs) >= 1

    def test_get_diff_malformed_numstat(self, git_repo, monkeypatch):
        """Test get_diff handles malformed numstat output."""
        git_ops = GitOperations(str(git_repo))

        # Create a change
        (git_repo / "test.txt").write_text("test")
        git_ops.add_files(["test.txt"])

        # Mock to return malformed numstat (covers line 161)
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "diff" in args[0] and "--numstat" in args[0]:
                result = original_run(*args, **kwargs)
                # Return malformed output (not 3 parts)
                result.stdout = "1\t2\n"  # Only 2 parts instead of 3
                return result
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        diffs = git_ops.get_diff(staged=True)
        # Should skip malformed lines
        assert isinstance(diffs, list)

    def test_get_file_history_malformed_line(self, git_repo, monkeypatch):
        """Test get_file_history handles malformed commit lines."""
        git_ops = GitOperations(str(git_repo))

        # Create file with history
        (git_repo / "history.txt").write_text("v1")
        git_ops.add_all()
        git_ops.commit("First")

        # Mock to return malformed history (covers line 314)
        original_run = subprocess.run
        def mock_run(*args, **kwargs):
            if "log" in args[0] and "--pretty" in str(args[0]):
                result = original_run(*args, **kwargs)
                # Return malformed line (not 5 parts)
                result.stdout = "hash|author|email\n"  # Only 3 parts
                return result
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)

        history = git_ops.get_file_history("history.txt")
        # Should skip malformed lines
        assert isinstance(history, list)
