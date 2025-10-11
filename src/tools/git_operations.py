"""
Git Operations

Git integration utilities for Devmatrix agents.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class GitStatus:
    """Git repository status."""

    branch: str
    is_clean: bool
    staged_files: List[str]
    modified_files: List[str]
    untracked_files: List[str]
    ahead: int
    behind: int


@dataclass
class GitDiff:
    """Git diff result."""

    file_path: str
    additions: int
    deletions: int
    diff_content: str


class GitOperations:
    """
    Git operation utilities.

    Usage:
        git_ops = GitOperations(repo_path="/path/to/repo")
        status = git_ops.get_status()
        diff = git_ops.get_diff("file.py")
    """

    def __init__(self, repo_path: str):
        """
        Initialize git operations.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path).resolve()

        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")

    def _run_command(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """
        Run git command.

        Args:
            args: Command arguments
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result
        """
        return subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=check,
        )

    def get_status(self) -> GitStatus:
        """
        Get repository status.

        Returns:
            GitStatus object
        """
        # Get current branch
        result = self._run_command(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = result.stdout.strip()

        # Get status
        result = self._run_command(["status", "--porcelain"])
        status_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        staged = []
        modified = []
        untracked = []

        for line in status_lines:
            if not line:
                continue

            status_code = line[:2]
            file_path = line[3:]

            if status_code[0] in "MADRC":  # Staged
                staged.append(file_path)
            if status_code[1] == "M":  # Modified
                modified.append(file_path)
            if status_code == "??":  # Untracked
                untracked.append(file_path)

        # Get ahead/behind
        ahead, behind = 0, 0
        result = self._run_command(
            ["rev-list", "--left-right", "--count", f"{branch}...@{{u}}"],
            check=False
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])

        is_clean = len(staged) == 0 and len(modified) == 0 and len(untracked) == 0

        return GitStatus(
            branch=branch,
            is_clean=is_clean,
            staged_files=staged,
            modified_files=modified,
            untracked_files=untracked,
            ahead=ahead,
            behind=behind,
        )

    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> List[GitDiff]:
        """
        Get diff for file(s).

        Args:
            file_path: Specific file path (None for all)
            staged: Show staged diff

        Returns:
            List of GitDiff objects
        """
        args = ["diff", "--numstat"]
        if staged:
            args.append("--cached")
        if file_path:
            args.append("--")
            args.append(file_path)

        result = self._run_command(args)
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        diffs = []
        for line in lines:
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) != 3:
                continue

            additions = int(parts[0]) if parts[0] != "-" else 0
            deletions = int(parts[1]) if parts[1] != "-" else 0
            filepath = parts[2]

            # Get actual diff content
            diff_args = ["diff"]
            if staged:
                diff_args.append("--cached")
            diff_args.extend(["--", filepath])

            diff_result = self._run_command(diff_args)

            diffs.append(
                GitDiff(
                    file_path=filepath,
                    additions=additions,
                    deletions=deletions,
                    diff_content=diff_result.stdout,
                )
            )

        return diffs

    def add_files(self, file_paths: List[str]) -> bool:
        """
        Stage files for commit.

        Args:
            file_paths: List of file paths to stage

        Returns:
            True if successful
        """
        try:
            self._run_command(["add"] + file_paths)
            return True
        except subprocess.CalledProcessError:
            return False

    def add_all(self) -> bool:
        """
        Stage all changes.

        Returns:
            True if successful
        """
        try:
            self._run_command(["add", "-A"])
            return True
        except subprocess.CalledProcessError:
            return False

    def commit(self, message: str, author: Optional[str] = None) -> bool:
        """
        Create commit.

        Args:
            message: Commit message
            author: Optional author string

        Returns:
            True if successful
        """
        try:
            args = ["commit", "-m", message]
            if author:
                args.extend(["--author", author])

            self._run_command(args)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_last_commit(self) -> Dict[str, Any]:
        """
        Get last commit information.

        Returns:
            Dictionary with commit info
        """
        result = self._run_command([
            "log", "-1", "--pretty=format:%H%n%an%n%ae%n%at%n%s"
        ])

        lines = result.stdout.strip().split("\n")
        if len(lines) < 5:
            return {}

        return {
            "hash": lines[0],
            "author_name": lines[1],
            "author_email": lines[2],
            "timestamp": int(lines[3]),
            "message": lines[4],
        }

    def get_changed_files(self, since_commit: str = "HEAD~1") -> List[str]:
        """
        Get files changed since commit.

        Args:
            since_commit: Commit reference (default: HEAD~1)

        Returns:
            List of changed file paths
        """
        result = self._run_command([
            "diff", "--name-only", since_commit, "HEAD"
        ])

        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [f for f in files if f]

    def is_file_tracked(self, file_path: str) -> bool:
        """
        Check if file is tracked by git.

        Args:
            file_path: Path to file

        Returns:
            True if tracked
        """
        result = self._run_command(
            ["ls-files", "--error-unmatch", file_path],
            check=False
        )
        return result.returncode == 0

    def get_file_history(self, file_path: str, max_count: int = 10) -> List[Dict[str, Any]]:
        """
        Get commit history for file.

        Args:
            file_path: Path to file
            max_count: Maximum commits to retrieve

        Returns:
            List of commit dictionaries
        """
        result = self._run_command([
            "log",
            f"--max-count={max_count}",
            "--pretty=format:%H|%an|%ae|%at|%s",
            "--",
            file_path
        ])

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "author_name": parts[1],
                    "author_email": parts[2],
                    "timestamp": int(parts[3]),
                    "message": parts[4],
                })

        return commits

    def get_branch_name(self) -> str:
        """
        Get current branch name.

        Returns:
            Branch name
        """
        result = self._run_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """
        Get remote URL.

        Args:
            remote: Remote name (default: origin)

        Returns:
            Remote URL or None
        """
        result = self._run_command(
            ["remote", "get-url", remote],
            check=False
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def get_uncommitted_changes(self) -> Dict[str, List[str]]:
        """
        Get summary of uncommitted changes.

        Returns:
            Dictionary with categorized changes
        """
        status = self.get_status()

        return {
            "staged": status.staged_files,
            "modified": status.modified_files,
            "untracked": status.untracked_files,
            "total": len(status.staged_files) + len(status.modified_files) + len(status.untracked_files)
        }
