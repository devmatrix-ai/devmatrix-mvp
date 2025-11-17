"""Tests for plan visualizer."""

import pytest
from src.console.plan_visualizer import (
    Phase,
    Task,
    MasterPlan,
    PlanVisualizer,
)


@pytest.fixture
def sample_phases():
    """Create sample phases."""
    return [
        Phase(number=0, name="Discovery", task_count=5, completed=5, emoji="✅"),
        Phase(number=1, name="Analysis", task_count=15, completed=15, emoji="✅"),
        Phase(number=2, name="Planning", task_count=20, completed=10, emoji="🔄"),
        Phase(number=3, name="Execution", task_count=70, completed=0, emoji="⏳"),
        Phase(number=4, name="Validation", task_count=10, completed=0, emoji="⏳"),
    ]


@pytest.fixture
def sample_tasks():
    """Create sample tasks."""
    return [
        Task(
            id="task_001",
            name="Analyze requirements",
            phase=0,
            phase_name="Discovery",
            status="completed",
            estimated_duration_ms=2000,
        ),
        Task(
            id="task_002",
            name="Define data model",
            phase=1,
            phase_name="Analysis",
            status="completed",
            estimated_duration_ms=3000,
            dependencies=["task_001"],
        ),
        Task(
            id="task_003",
            name="Design architecture",
            phase=2,
            phase_name="Planning",
            status="in_progress",
            estimated_duration_ms=5000,
            dependencies=["task_002"],
        ),
        Task(
            id="task_004",
            name="Implement models",
            phase=3,
            phase_name="Execution",
            status="pending",
            estimated_duration_ms=8000,
            dependencies=["task_003"],
        ),
    ]


@pytest.fixture
def sample_masterplan(sample_phases, sample_tasks):
    """Create a sample masterplan."""
    return MasterPlan(
        execution_id="exec_20251116_abc123",
        total_tasks=120,
        phases=sample_phases,
        tasks=sample_tasks,
        estimated_total_duration_ms=600000,
        total_tokens_estimated=67450,
    )


class TestPhaseModel:
    """Test Phase dataclass."""

    def test_phase_creation(self):
        """Test phase creation."""
        phase = Phase(number=0, name="Discovery", task_count=10)
        assert phase.number == 0
        assert phase.name == "Discovery"
        assert phase.task_count == 10
        assert phase.completed == 0
        assert phase.emoji == "⏳"

    def test_phase_with_completion(self):
        """Test phase with completion."""
        phase = Phase(number=1, name="Analysis", task_count=15, completed=10)
        assert phase.completed == 10
        assert phase.task_count == 15


class TestTaskModel:
    """Test Task dataclass."""

    def test_task_creation(self):
        """Test task creation."""
        task = Task(
            id="task_001",
            name="Test task",
            phase=0,
            phase_name="Discovery",
            status="pending",
        )
        assert task.id == "task_001"
        assert task.name == "Test task"
        assert task.status == "pending"

    def test_task_status_emoji(self):
        """Test task status emoji."""
        completed_task = Task(
            id="task_001",
            name="Done",
            phase=0,
            phase_name="Discovery",
            status="completed",
        )
        assert completed_task.status_emoji == "✅"

        pending_task = Task(
            id="task_002",
            name="Pending",
            phase=0,
            phase_name="Discovery",
            status="pending",
        )
        assert pending_task.status_emoji == "⏳"

        failed_task = Task(
            id="task_003",
            name="Failed",
            phase=0,
            phase_name="Discovery",
            status="failed",
        )
        assert failed_task.status_emoji == "❌"

    def test_task_with_dependencies(self):
        """Test task with dependencies."""
        task = Task(
            id="task_002",
            name="Dependent task",
            phase=1,
            phase_name="Analysis",
            status="pending",
            dependencies=["task_001"],
        )
        assert len(task.dependencies) == 1
        assert "task_001" in task.dependencies


class TestMasterPlanModel:
    """Test MasterPlan dataclass."""

    def test_masterplan_creation(self, sample_phases, sample_tasks):
        """Test masterplan creation."""
        plan = MasterPlan(
            execution_id="exec_001",
            total_tasks=120,
            phases=sample_phases,
            tasks=sample_tasks,
        )
        assert plan.execution_id == "exec_001"
        assert plan.total_tasks == 120
        assert len(plan.phases) == 5
        assert len(plan.tasks) == 4

    def test_masterplan_with_estimates(self, sample_phases, sample_tasks):
        """Test masterplan with time and token estimates."""
        plan = MasterPlan(
            execution_id="exec_001",
            total_tasks=120,
            phases=sample_phases,
            tasks=sample_tasks,
            estimated_total_duration_ms=600000,
            total_tokens_estimated=67450,
        )
        assert plan.estimated_total_duration_ms == 600000
        assert plan.total_tokens_estimated == 67450


class TestPlanVisualizer:
    """Test PlanVisualizer."""

    def test_visualizer_initialization(self):
        """Test visualizer initialization."""
        visualizer = PlanVisualizer()
        assert visualizer.console is not None

    def test_motivational_message(self):
        """Test motivational messages."""
        visualizer = PlanVisualizer()

        msg_0 = visualizer.motivational_message(0)
        assert "amazing" in msg_0.lower()

        msg_50 = visualizer.motivational_message(50)
        assert "halfway" in msg_50.lower()

        msg_100 = visualizer.motivational_message(100)
        assert "legendary" in msg_100.lower()

    def test_phase_message(self):
        """Test phase messages."""
        visualizer = PlanVisualizer()

        msg_0 = visualizer.phase_message(0)
        assert "Discovery" in msg_0

        msg_2 = visualizer.phase_message(2)
        assert "Planning" in msg_2

        msg_3 = visualizer.phase_message(3)
        assert "Execution" in msg_3

    def test_show_masterplan_overview(self, sample_masterplan, capsys):
        """Test showing masterplan overview."""
        visualizer = PlanVisualizer()
        visualizer.show_masterplan_overview(sample_masterplan)

        captured = capsys.readouterr()
        assert "MASTERPLAN" in captured.out
        assert "Quick Stats" in captured.out
        assert "120" in captured.out

    def test_show_phases_timeline(self, sample_masterplan, capsys):
        """Test showing phases timeline."""
        visualizer = PlanVisualizer()
        visualizer.show_phases_timeline(sample_masterplan)

        captured = capsys.readouterr()
        assert "PHASES TIMELINE" in captured.out
        assert "Discovery" in captured.out
        assert "Analysis" in captured.out

    def test_show_tasks_table(self, sample_masterplan, capsys):
        """Test showing tasks table."""
        visualizer = PlanVisualizer()
        visualizer.show_tasks_table(sample_masterplan)

        captured = capsys.readouterr()
        assert "TASKS" in captured.out
        assert "Analyze requirements" in captured.out

    def test_show_statistics(self, sample_masterplan, capsys):
        """Test showing statistics."""
        visualizer = PlanVisualizer()
        visualizer.show_statistics(sample_masterplan)

        captured = capsys.readouterr()
        assert "STATISTICS" in captured.out
        assert "Completed" in captured.out

    def test_show_full_plan(self, sample_masterplan, capsys):
        """Test showing full plan."""
        visualizer = PlanVisualizer()
        visualizer.show_full_plan(sample_masterplan)

        captured = capsys.readouterr()
        assert "MASTERPLAN" in captured.out
        assert "Quick Stats" in captured.out


class TestVisualizerIntegration:
    """Integration tests for visualizer."""

    def test_visualizer_with_real_data(self, sample_masterplan):
        """Test visualizer with realistic data."""
        visualizer = PlanVisualizer()

        # Should not raise any exceptions
        visualizer.show_masterplan_overview(sample_masterplan)
        visualizer.show_phases_timeline(sample_masterplan)
        visualizer.show_tasks_table(sample_masterplan)
        visualizer.show_statistics(sample_masterplan)

    def test_completion_calculation(self, sample_masterplan):
        """Test completion percentage calculation."""
        total_completed = sum(p.completed for p in sample_masterplan.phases)
        completion = (total_completed / sample_masterplan.total_tasks) * 100

        # Discovery (5/5) + Analysis (15/15) + Planning (10/20) = 30/120
        assert completion == 25.0

    def test_phase_dependencies(self, sample_masterplan):
        """Test finding dependent tasks."""
        # Task 002 depends on task 001
        task_001 = sample_masterplan.tasks[0]
        task_002 = sample_masterplan.tasks[1]

        assert task_001.id in task_002.dependencies

    def test_root_tasks_identification(self, sample_masterplan):
        """Test identifying root tasks (no dependencies)."""
        root_tasks = [
            t for t in sample_masterplan.tasks
            if not t.dependencies or len(t.dependencies) == 0
        ]

        # Only task_001 has no dependencies
        assert len(root_tasks) == 1
        assert root_tasks[0].id == "task_001"
