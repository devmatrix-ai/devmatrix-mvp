"""
File Operations Demo

Demonstrates the file operation tools for Devmatrix agents:
- WorkspaceManager: Isolated temporary workspaces
- FileOperations: Safe file manipulation
- GitOperations: Version control integration
"""

from src.tools.workspace_manager import WorkspaceManager
from src.tools.file_operations import FileOperations
from src.tools.git_operations import GitOperations
import subprocess


def demo_workspace_manager():
    """Demonstrate WorkspaceManager features."""
    print("=" * 60)
    print("WORKSPACE MANAGER DEMO")
    print("=" * 60)

    # Create workspace with context manager (auto-cleanup)
    with WorkspaceManager() as workspace:
        print(f"\n✓ Created workspace: {workspace.base_path}")

        # Write files
        workspace.write_file("README.md", "# My Project\n\nThis is a demo project.")
        workspace.write_file("src/main.py", "print('Hello, World!')")
        workspace.write_file("src/utils.py", "def helper(): pass")
        print("✓ Created 3 files")

        # List files
        files = workspace.list_files("src", "*.py")
        print(f"✓ Found {len(files)} Python files in src/: {files}")

        # Check workspace size
        size = workspace.get_size()
        print(f"✓ Workspace size: {size} bytes")

        # Read file
        content = workspace.read_file("README.md")
        print(f"✓ Read README.md: {content[:30]}...")

        # Demonstrate path traversal protection
        try:
            workspace.write_file("../../../etc/passwd", "malicious")
        except ValueError as e:
            print(f"✓ Path traversal protection: {e}")

    print("✓ Workspace auto-cleaned on exit")


def demo_file_operations():
    """Demonstrate FileOperations features."""
    print("\n" + "=" * 60)
    print("FILE OPERATIONS DEMO")
    print("=" * 60)

    with WorkspaceManager() as workspace:
        file_ops = FileOperations(str(workspace.base_path))
        print(f"\n✓ Initialized FileOperations at: {workspace.base_path}")

        # Write and read
        file_ops.write_file("data.txt", "Original content")
        content = file_ops.read_file("data.txt")
        print(f"✓ Write and read: {content}")

        # Append
        file_ops.append_file("data.txt", "\nAppended line")
        content = file_ops.read_file("data.txt")
        print(f"✓ Appended: {content}")

        # Copy
        file_ops.copy_file("data.txt", "data_backup.txt")
        print("✓ Copied data.txt → data_backup.txt")

        # File info
        info = file_ops.get_file_info("data.txt")
        print(f"✓ File info: {info['name']}, {info['size']} bytes")

        # File hash
        hash_value = file_ops.get_file_hash("data.txt")
        print(f"✓ SHA256 hash: {hash_value[:16]}...")

        # List files with pattern
        file_ops.write_file("test1.py", "# test 1")
        file_ops.write_file("test2.py", "# test 2")
        file_ops.write_file("doc.md", "# doc")

        py_files = file_ops.list_files("", "*.py")
        print(f"✓ Found {len(py_files)} Python files: {py_files}")

        # Directory tree
        file_ops.write_file("src/app.py", "# app")
        file_ops.write_file("src/lib/helper.py", "# helper")
        tree = file_ops.get_tree(max_depth=2)
        print(f"✓ Directory tree: {tree['type']} with {len(tree['children'])} items")

        # Move file
        file_ops.move_file("data_backup.txt", "backups/data_backup.txt")
        print("✓ Moved file to backups/")

        # Unicode support
        file_ops.write_file("unicode.txt", "Hello 世界 🚀")
        unicode_content = file_ops.read_file("unicode.txt")
        print(f"✓ Unicode support: {unicode_content}")


def demo_git_operations():
    """Demonstrate GitOperations features."""
    print("\n" + "=" * 60)
    print("GIT OPERATIONS DEMO")
    print("=" * 60)

    with WorkspaceManager() as workspace:
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=workspace.base_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Demo User"],
            cwd=workspace.base_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "demo@example.com"],
            cwd=workspace.base_path,
            check=True,
            capture_output=True,
        )
        print(f"\n✓ Initialized git repository at: {workspace.base_path}")

        git_ops = GitOperations(str(workspace.base_path))

        # Create initial files
        workspace.write_file("README.md", "# Project\n\nInitial version.")
        workspace.write_file("main.py", "print('v1')")
        print("✓ Created initial files")

        # Stage and commit (need at least one commit before get_status works)
        git_ops.add_all()
        git_ops.commit("Initial commit")
        print("✓ Created initial commit")

        # Check status after initial commit
        status = git_ops.get_status()
        print(f"✓ Status: branch={status.branch}, clean={status.is_clean}")

        # Modify files
        workspace.write_file("README.md", "# Project\n\nUpdated version.")
        workspace.write_file("new_file.py", "print('new')")

        # Check uncommitted changes
        changes = git_ops.get_uncommitted_changes()
        print(f"✓ Uncommitted changes: {changes['total']} files")
        print(f"  - Modified: {changes['modified']}")
        print(f"  - Untracked: {changes['untracked']}")

        # Get diff
        diffs = git_ops.get_diff()
        if diffs:
            diff = diffs[0]
            print(f"✓ Diff: {diff.file_path} (+{diff.additions}/-{diff.deletions})")

        # Stage and commit changes
        git_ops.add_all()
        git_ops.commit("Update README and add new file")
        print("✓ Created second commit")

        # Get commit history
        last_commit = git_ops.get_last_commit()
        print(f"✓ Last commit: {last_commit['message']}")
        print(f"  Author: {last_commit['author_name']} <{last_commit['author_email']}>")

        # File history
        history = git_ops.get_file_history("README.md", max_count=5)
        print(f"✓ README.md history: {len(history)} commits")

        # Check if file is tracked
        is_tracked = git_ops.is_file_tracked("README.md")
        print(f"✓ README.md tracked: {is_tracked}")

        # Get changed files
        changed = git_ops.get_changed_files(since_commit="HEAD~1")
        print(f"✓ Files changed in last commit: {changed}")


def demo_integrated_workflow():
    """Demonstrate integrated workflow with all tools."""
    print("\n" + "=" * 60)
    print("INTEGRATED WORKFLOW DEMO")
    print("=" * 60)

    with WorkspaceManager() as workspace:
        print(f"\n✓ Workspace: {workspace.base_path}")

        # Initialize git
        subprocess.run(["git", "init"], cwd=workspace.base_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Agent"],
            cwd=workspace.base_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "agent@devmatrix.com"],
            cwd=workspace.base_path,
            check=True,
            capture_output=True,
        )

        file_ops = FileOperations(str(workspace.base_path))
        git_ops = GitOperations(str(workspace.base_path))

        # 1. Create project structure
        print("\n📁 Creating project structure...")
        file_ops.write_file("README.md", "# AI Agent Project")
        file_ops.write_file("src/agent.py", "class Agent:\n    pass")
        file_ops.write_file("src/tools.py", "# Tools")
        file_ops.write_file("tests/test_agent.py", "# Tests")

        # 2. Initial commit
        print("📝 Initial commit...")
        git_ops.add_all()
        git_ops.commit("Initial project structure")

        # 3. Develop feature
        print("🔨 Developing feature...")
        agent_code = """class Agent:
    def __init__(self, name):
        self.name = name

    def execute(self, task):
        print(f"{self.name} executing: {task}")
"""
        file_ops.write_file("src/agent.py", agent_code)

        # 4. Check what changed
        print("🔍 Checking changes...")
        status = git_ops.get_status()
        print(f"   Modified files: {status.modified_files}")

        diffs = git_ops.get_diff()
        for diff in diffs:
            print(f"   {diff.file_path}: +{diff.additions}/-{diff.deletions} lines")

        # 5. Commit feature
        print("✅ Committing feature...")
        git_ops.add_all()
        git_ops.commit("Add Agent implementation with execute method")

        # 6. Add tests
        print("🧪 Adding tests...")
        test_code = """def test_agent_creation():
    agent = Agent("TestAgent")
    assert agent.name == "TestAgent"

def test_agent_execute():
    agent = Agent("TestAgent")
    agent.execute("task")  # Should not raise
"""
        file_ops.write_file("tests/test_agent.py", test_code)

        # 7. Get file info
        info = file_ops.get_file_info("src/agent.py")
        print(f"📄 src/agent.py: {info['size']} bytes")

        # 8. Get commit history
        history = git_ops.get_file_history("src/agent.py", max_count=5)
        print(f"📜 src/agent.py history: {len(history)} commits")

        # 9. Final commit
        git_ops.add_all()
        git_ops.commit("Add agent tests")

        # 10. Summary
        print("\n📊 Summary:")
        all_files = file_ops.list_files("", "*", recursive=True)
        print(f"   Total files: {len(all_files)}")

        last_commit = git_ops.get_last_commit()
        print(f"   Last commit: {last_commit['message']}")

        total_size = 0
        for f in all_files:
            info = file_ops.get_file_info(f)
            total_size += info['size']
        print(f"   Total size: {total_size} bytes")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DEVMATRIX FILE OPERATIONS DEMO")
    print("=" * 60)
    print("\nDemonstrating tools for AI agent file manipulation:\n")
    print("1. WorkspaceManager - Isolated temporary workspaces")
    print("2. FileOperations - Safe file manipulation")
    print("3. GitOperations - Version control integration")
    print("4. Integrated Workflow - Real-world usage")

    try:
        demo_workspace_manager()
        demo_file_operations()
        demo_git_operations()
        demo_integrated_workflow()

        print("\n" + "=" * 60)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
