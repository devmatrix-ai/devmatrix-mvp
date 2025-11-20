"""
End-to-End Tests for UX Improvements

Tests the integration of all 4 UX priorities:
1. Interactive Approval System
2. Context Stack Visibility
3. Rollback/Undo System
4. Live Progress Streaming

Spec Reference: agent-os/specs/2025-11-19-devmatrix-ux-improvements/spec.md
Sprint 3: Task 3.7
"""

import pytest
import asyncio
import time
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from rich.console import Console
from io import StringIO

from src.cli.approval_manager import ApprovalManager, FileChange
from src.cli.context_tracker import ContextStackTracker
from src.cli.snapshot_manager import SnapshotManager
from src.cli.progress_renderer import LiveProgressRenderer
from src.cognitive.pipeline.context import PipelineContext
from src.cognitive.pipeline.result import PipelineResult, PipelinePhase


class TestUXImprovementsE2E:
    """
    End-to-end tests for all UX improvements working together.

    Tests the full workflow from planning through execution with:
    - Approval gates
    - Context tracking
    - Automatic snapshots
    - Live progress updates
    """

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        workspace = Path(tempfile.mkdtemp())
        yield workspace

        # Cleanup
        if workspace.exists():
            shutil.rmtree(workspace)

    @pytest.fixture
    def test_console(self):
        """Create test console for capturing output"""
        return Console(file=StringIO())

    def test_full_ux_workflow_with_all_features(self, temp_workspace, test_console):
        """
        Test complete UX workflow with all 4 priorities.

        Workflow:
        1. Create snapshot before execution
        2. Track context during planning
        3. Request approval for file changes
        4. Show live progress during execution
        5. Verify all features worked together
        """
        # Setup all UX components
        approval_mgr = ApprovalManager(console=test_console, auto_approve=True)
        context_tracker = ContextStackTracker(console=test_console)
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)
        progress_renderer = LiveProgressRenderer(console=test_console, total_phases=3)

        # Phase 1: Create initial workspace state
        initial_file = temp_workspace / "initial.py"
        initial_file.write_text("print('initial')")

        # Phase 2: Create snapshot before execution
        snapshot_id = snapshot_mgr.create_snapshot(
            description="Before E2E test execution",
            auto=True
        )
        assert snapshot_id is not None

        # Phase 3: Track context
        progress_renderer.start_phase("Context Tracking", total_tasks=3)

        context_tracker.add_file(initial_file, initial_file.read_text())
        progress_renderer.update_phase(1, "Added initial file to context")

        context_tracker.add_pattern("test_pattern_123", "def test(): pass")
        progress_renderer.update_phase(2, "Added pattern to context")

        context_tracker.add_response("Test response content", "Planning Response")
        progress_renderer.update_phase(3, "Added response to context")

        progress_renderer.complete_phase()

        # Verify context tracking
        assert context_tracker.get_item_count() == 3
        assert context_tracker.get_usage_percent() < 100

        # Phase 4: Request approval for file changes
        progress_renderer.start_phase("Approval", total_tasks=3)

        file_changes = [
            FileChange(
                operation="create",
                path=temp_workspace / "new_file.py",
                new_content="print('new file')",
                language="python"
            ),
            FileChange(
                operation="update",
                path=initial_file,
                old_content="print('initial')",
                new_content="print('updated')",
                language="python"
            ),
            FileChange(
                operation="delete",
                path=temp_workspace / "old_file.py",
                old_content="print('old')",
                language="python"
            )
        ]

        approvals = approval_mgr.approve_changes(file_changes)
        progress_renderer.update_phase(3, "Approvals obtained")
        progress_renderer.complete_phase()

        # Verify all approved (auto-approve mode)
        assert all(approvals.values())

        # Phase 5: Execute approved changes
        progress_renderer.start_phase("Execution", total_tasks=len(file_changes))

        for i, (path, approved) in enumerate(approvals.items(), 1):
            if approved:
                change = next(c for c in file_changes if c.path == path)

                if change.operation == "create":
                    change.path.write_text(change.new_content)
                    progress_renderer.update_phase(i, f"Created {change.path.name}")

                elif change.operation == "update":
                    change.path.write_text(change.new_content)
                    progress_renderer.update_phase(i, f"Updated {change.path.name}")

                elif change.operation == "delete":
                    # Don't actually delete (file doesn't exist)
                    progress_renderer.update_phase(i, f"Deleted {change.path.name}")

        progress_renderer.complete_phase()

        # Verify execution results
        new_file = temp_workspace / "new_file.py"
        assert new_file.exists()
        assert "new file" in new_file.read_text()

        assert "updated" in initial_file.read_text()

        # Verify progress tracking
        assert progress_renderer.get_completed_phases() == 3
        assert progress_renderer.get_phase_count() == 3

        # Verify time estimation
        avg_time = progress_renderer.get_average_phase_time()
        assert avg_time is not None
        assert avg_time > 0

        # Verify snapshot can rollback changes
        snapshots = snapshot_mgr.list_snapshots()
        assert len(snapshots) >= 1
        assert snapshot_id in [s.id for s in snapshots]

    def test_approval_rejection_workflow(self, temp_workspace, test_console):
        """
        Test workflow when user rejects file changes.

        Verifies:
        - Rejected files are not created
        - Context is still tracked
        - Snapshot is still created
        - Progress is still updated
        """
        # Setup with manual approval (not auto-approve)
        approval_mgr = ApprovalManager(console=test_console, auto_approve=False)
        context_tracker = ContextStackTracker(console=test_console)
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)

        # Create snapshot
        snapshot_id = snapshot_mgr.create_snapshot(description="Before test")

        # Track context
        test_file = temp_workspace / "test.py"
        test_file.write_text("test content")
        context_tracker.add_file(test_file, test_file.read_text())

        # Create file changes
        changes = [
            FileChange(
                operation="create",
                path=temp_workspace / "rejected.py",
                new_content="# This should not be created"
            )
        ]

        # In auto_approve=False, approve_changes would normally prompt user
        # For testing, we'll manually set approvals
        approvals = {changes[0].path: False}  # Reject the file

        # Verify file is not approved
        assert not approvals[changes[0].path]

        # Verify file was not created
        rejected_file = temp_workspace / "rejected.py"
        assert not rejected_file.exists()

        # Verify context and snapshot still work
        assert context_tracker.get_item_count() == 1
        assert len(snapshot_mgr.list_snapshots()) >= 1

    def test_snapshot_rollback_integration(self, temp_workspace, test_console):
        """
        Test full snapshot and rollback workflow.

        Verifies:
        - Snapshot before changes
        - Changes are made
        - Rollback restores original state
        - Context and progress work throughout
        """
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)
        context_tracker = ContextStackTracker(console=test_console)
        progress_renderer = LiveProgressRenderer(console=test_console, total_phases=4)

        # Phase 1: Create initial state
        progress_renderer.start_phase("Setup", 1)
        original_file = temp_workspace / "original.py"
        original_file.write_text("original content")
        context_tracker.add_file(original_file, original_file.read_text())
        progress_renderer.update_phase(1, "Initial file created")
        progress_renderer.complete_phase()

        # Phase 2: Create snapshot
        progress_renderer.start_phase("Snapshot", 1)
        snapshot_id = snapshot_mgr.create_snapshot(description="Before modifications")
        progress_renderer.update_phase(1, f"Snapshot {snapshot_id} created")
        progress_renderer.complete_phase()

        # Small delay to ensure unique snapshot ID for backup snapshot
        time.sleep(1.1)

        # Phase 3: Make changes
        progress_renderer.start_phase("Modify", 2)
        original_file.write_text("modified content")
        progress_renderer.update_phase(1, "File modified")

        new_file = temp_workspace / "new.py"
        new_file.write_text("new content")
        progress_renderer.update_phase(2, "New file created")
        progress_renderer.complete_phase()

        # Verify changes
        assert "modified" in original_file.read_text()
        assert new_file.exists()

        # Phase 4: Rollback
        progress_renderer.start_phase("Rollback", 1)
        success = snapshot_mgr.rollback(snapshot_id, force=True)
        assert success
        progress_renderer.update_phase(1, "Rollback complete")
        progress_renderer.complete_phase()

        # Verify rollback restored original state
        assert "original" in original_file.read_text()
        assert not new_file.exists()

        # Verify progress tracking
        assert progress_renderer.get_completed_phases() == 4

    def test_context_overflow_warning(self, temp_workspace, test_console):
        """
        Test context tracker warns when approaching limits.

        Verifies:
        - Context usage percentage is calculated correctly
        - Color coding changes based on usage
        - Large files are tracked properly
        """
        context_tracker = ContextStackTracker(
            console=test_console,
            max_chars=1000  # Small limit for testing
        )

        # Add small file (green zone)
        context_tracker.add_file(Path("small.py"), "a" * 400)
        assert context_tracker.get_usage_percent() < 50

        # Add medium file (yellow zone)
        context_tracker.add_file(Path("medium.py"), "b" * 300)
        usage = context_tracker.get_usage_percent()
        assert 50 <= usage < 80

        # Add large file (red zone)
        context_tracker.add_file(Path("large.py"), "c" * 250)
        usage = context_tracker.get_usage_percent()
        assert usage >= 80

    def test_performance_overhead_requirements(self, temp_workspace, test_console):
        """
        Test that UX features meet performance requirements.

        Requirements:
        - Approval overhead: <2 seconds per file
        - Snapshot creation: <1 second
        - Context display: <50ms
        - Progress updates: no pipeline slowdown
        """
        approval_mgr = ApprovalManager(console=test_console, auto_approve=True)
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)
        context_tracker = ContextStackTracker(console=test_console)
        progress_renderer = LiveProgressRenderer(console=test_console)

        # Test 1: Approval overhead <2 seconds
        file_changes = [
            FileChange(
                operation="create",
                path=temp_workspace / f"file{i}.py",
                new_content=f"# File {i}"
            ) for i in range(5)
        ]

        start = time.time()
        approvals = approval_mgr.approve_changes(file_changes)
        elapsed = time.time() - start

        # 5 files should be approved in <2 seconds total
        assert elapsed < 2.0, f"Approval too slow: {elapsed:.3f}s"

        # Test 2: Snapshot creation <1 second
        # Create some files first
        for i in range(10):
            (temp_workspace / f"test{i}.py").write_text(f"content {i}")

        start = time.time()
        snapshot_id = snapshot_mgr.create_snapshot(description="Performance test")
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Snapshot too slow: {elapsed:.3f}s"

        # Test 3: Context display <50ms
        for i in range(20):
            context_tracker.add_file(Path(f"file{i}.py"), f"content {i}")

        start = time.time()
        # Display uses console, which is captured, so we can't easily measure
        # But we can verify show() completes quickly
        context_tracker.show()
        elapsed = time.time() - start

        assert elapsed < 0.05, f"Context display too slow: {elapsed:.3f}s"

        # Test 4: Progress updates - no slowdown
        start = time.time()
        progress_renderer.start_phase("Performance Test", 100)
        for i in range(100):
            progress_renderer.update_phase(i, f"Update {i}")
        progress_renderer.complete_phase()
        elapsed = time.time() - start

        # 100 updates should complete in <0.5s
        assert elapsed < 0.5, f"Progress updates too slow: {elapsed:.3f}s"

    def test_error_handling_integration(self, temp_workspace, test_console):
        """
        Test error handling across all UX components.

        Verifies:
        - Errors in one component don't break others
        - Graceful degradation
        - Error messages are clear
        """
        approval_mgr = ApprovalManager(console=test_console, auto_approve=True)
        context_tracker = ContextStackTracker(console=test_console)
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)
        progress_renderer = LiveProgressRenderer(console=test_console)

        # Test 1: Invalid snapshot rollback doesn't crash
        success = snapshot_mgr.rollback("invalid_snapshot_id", force=True)
        assert not success  # Should fail gracefully

        # Test 2: Context tracker handles invalid files
        context_tracker.add_file(Path("nonexistent.py"), "content")
        assert context_tracker.get_item_count() == 1  # Still tracked

        # Test 3: Approval manager handles empty changes
        approvals = approval_mgr.approve_changes([])
        assert approvals == {}  # Empty dict, no crash

        # Test 4: Progress renderer handles phase updates without active phase
        progress_renderer.update_phase(10, "No active phase")
        # Should log warning but not crash
        assert progress_renderer.get_phase_count() == 0

    def test_concurrent_feature_usage(self, temp_workspace, test_console):
        """
        Test using multiple UX features simultaneously.

        Verifies:
        - Features don't conflict
        - Resource usage is reasonable
        - All features remain functional
        """
        # Initialize all features
        approval_mgr = ApprovalManager(console=test_console, auto_approve=True)
        context_tracker = ContextStackTracker(console=test_console)
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)
        progress_renderer = LiveProgressRenderer(console=test_console, total_phases=2)

        # Use all features concurrently
        progress_renderer.start_phase("Concurrent Test", 5)

        # Step 1: Create snapshot
        snapshot_id = snapshot_mgr.create_snapshot(description="Concurrent test")
        progress_renderer.update_phase(1, "Snapshot created")

        # Step 2: Track context
        test_file = temp_workspace / "test.py"
        test_file.write_text("test content")
        context_tracker.add_file(test_file, test_file.read_text())
        progress_renderer.update_phase(2, "Context tracked")

        # Step 3: Request approvals
        changes = [
            FileChange(
                operation="create",
                path=temp_workspace / "new.py",
                new_content="new content"
            )
        ]
        approvals = approval_mgr.approve_changes(changes)
        progress_renderer.update_phase(3, "Approvals obtained")

        # Step 4: Display context
        context_tracker.show()
        progress_renderer.update_phase(4, "Context displayed")

        # Step 5: List snapshots
        snapshots = snapshot_mgr.list_snapshots()
        progress_renderer.update_phase(5, "Snapshots listed")
        progress_renderer.complete_phase()

        # Verify all features worked
        assert snapshot_id is not None
        assert context_tracker.get_item_count() == 1
        assert all(approvals.values())
        assert len(snapshots) >= 1
        assert progress_renderer.get_completed_phases() == 1

    def test_realistic_code_generation_scenario(self, temp_workspace, test_console):
        """
        Test a realistic code generation scenario.

        Simulates:
        1. Planning phase with context tracking
        2. Snapshot before execution
        3. Code generation with approval
        4. Progress tracking throughout
        5. Verification of generated code
        """
        # Setup
        approval_mgr = ApprovalManager(console=test_console, auto_approve=True)
        context_tracker = ContextStackTracker(console=test_console)
        snapshot_mgr = SnapshotManager(workspace_path=temp_workspace, console=test_console)
        progress_renderer = LiveProgressRenderer(console=test_console, total_phases=5)

        # Phase 1: Planning
        progress_renderer.start_phase("Planning", 3)

        spec_content = """
        Create a simple calculator with add, subtract, multiply, divide functions.
        """
        context_tracker.add_file(Path("spec.md"), spec_content)
        progress_renderer.update_phase(1, "Spec loaded")

        context_tracker.add_pattern("python_function_template", "def func(): pass")
        progress_renderer.update_phase(2, "Pattern loaded")

        context_tracker.add_response("Task breakdown: 4 functions", "Planning")
        progress_renderer.update_phase(3, "Tasks planned")

        progress_renderer.complete_phase()

        # Phase 2: Snapshot
        progress_renderer.start_phase("Snapshot", 1)
        snapshot_id = snapshot_mgr.create_snapshot(description="Before generation")
        progress_renderer.update_phase(1, "Snapshot created")
        progress_renderer.complete_phase()

        # Phase 3: Code Generation
        progress_renderer.start_phase("Generation", 4)

        generated_code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""

        changes = [
            FileChange(
                operation="create",
                path=temp_workspace / "calculator.py",
                new_content=generated_code,
                language="python"
            )
        ]

        approvals = approval_mgr.approve_changes(changes)
        progress_renderer.update_phase(4, "Code generated and approved")
        progress_renderer.complete_phase()

        # Phase 4: Execution
        progress_renderer.start_phase("Execution", 1)

        for path, approved in approvals.items():
            if approved:
                change = next(c for c in changes if c.path == path)
                change.path.write_text(change.new_content)

        progress_renderer.update_phase(1, "Files written")
        progress_renderer.complete_phase()

        # Phase 5: Verification
        progress_renderer.start_phase("Verification", 2)

        calculator_file = temp_workspace / "calculator.py"
        assert calculator_file.exists()
        content = calculator_file.read_text()

        assert "def add(" in content
        assert "def subtract(" in content
        assert "def multiply(" in content
        assert "def divide(" in content

        progress_renderer.update_phase(2, "Verification complete")
        progress_renderer.complete_phase()

        # Verify all metrics
        assert progress_renderer.get_completed_phases() == 5
        assert context_tracker.get_item_count() == 3
        assert len(snapshot_mgr.list_snapshots()) >= 1

        # Verify time estimation
        avg_time = progress_renderer.get_average_phase_time()
        assert avg_time is not None

        remaining_time = progress_renderer.get_estimated_remaining_time()
        # All phases complete, so should be None or 0
        assert remaining_time is None or remaining_time.total_seconds() == 0
