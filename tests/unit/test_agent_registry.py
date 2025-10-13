"""
Unit tests for AgentRegistry
"""

import pytest
from src.agents.agent_registry import (
    AgentRegistry,
    AgentCapability,
    TaskType,
    AgentMetadata,
    TASK_CAPABILITY_MAP
)


# Mock agent classes for testing
class MockCodeAgent:
    """Mock code generation agent."""

    def __init__(self, **kwargs):
        pass

    def execute(self, task, context):
        return {"success": True, "output": "code"}

    def get_capabilities(self):
        return {AgentCapability.CODE_GENERATION, AgentCapability.API_DESIGN}

    def get_name(self):
        return "mock_code_agent"


class MockTestAgent:
    """Mock testing agent."""

    def __init__(self, **kwargs):
        pass

    def execute(self, task, context):
        return {"success": True, "output": "tests"}

    def get_capabilities(self):
        return {AgentCapability.UNIT_TESTING, AgentCapability.INTEGRATION_TESTING}

    def get_name(self):
        return "mock_test_agent"


class MockDocAgent:
    """Mock documentation agent."""

    def __init__(self, **kwargs):
        pass

    def execute(self, task, context):
        return {"success": True, "output": "docs"}

    def get_capabilities(self):
        return {AgentCapability.API_DOCUMENTATION, AgentCapability.CODE_DOCUMENTATION}

    def get_name(self):
        return "mock_doc_agent"


class TestAgentRegistry:
    """Test suite for AgentRegistry."""

    @pytest.fixture
    def registry(self):
        """Create empty registry."""
        return AgentRegistry()

    @pytest.fixture
    def populated_registry(self, registry):
        """Create registry with test agents."""
        registry.register(
            name="code_gen",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION, AgentCapability.API_DESIGN},
            priority=10,
            description="Code generation agent"
        )

        registry.register(
            name="test_gen",
            agent_class=MockTestAgent,
            capabilities={AgentCapability.UNIT_TESTING, AgentCapability.INTEGRATION_TESTING},
            priority=8,
            description="Test generation agent"
        )

        registry.register(
            name="doc_gen",
            agent_class=MockDocAgent,
            capabilities={AgentCapability.API_DOCUMENTATION, AgentCapability.CODE_DOCUMENTATION},
            priority=5,
            description="Documentation generation agent"
        )

        return registry

    def test_init(self, registry):
        """Test registry initialization."""
        assert len(registry) == 0
        assert len(registry.get_capability_coverage()) > 0
        assert len(registry.get_task_type_coverage()) > 0

    def test_register_agent(self, registry):
        """Test registering an agent."""
        registry.register(
            name="test_agent",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION},
            priority=5
        )

        assert len(registry) == 1
        assert "test_agent" in registry

    def test_register_duplicate_name(self, registry):
        """Test registering agent with duplicate name."""
        registry.register(
            name="test_agent",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION}
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                name="test_agent",
                agent_class=MockTestAgent,
                capabilities={AgentCapability.UNIT_TESTING}
            )

    def test_register_no_capabilities(self, registry):
        """Test registering agent without capabilities."""
        with pytest.raises(ValueError, match="at least one capability"):
            registry.register(
                name="test_agent",
                agent_class=MockCodeAgent,
                capabilities=set()
            )

    def test_unregister_agent(self, populated_registry):
        """Test unregistering an agent."""
        assert "code_gen" in populated_registry
        assert len(populated_registry) == 3

        populated_registry.unregister("code_gen")

        assert "code_gen" not in populated_registry
        assert len(populated_registry) == 2

    def test_unregister_nonexistent_agent(self, registry):
        """Test unregistering nonexistent agent."""
        with pytest.raises(ValueError, match="not found"):
            registry.unregister("nonexistent")

    def test_get_agent_metadata(self, populated_registry):
        """Test getting agent metadata."""
        metadata = populated_registry.get_agent_metadata("code_gen")

        assert isinstance(metadata, AgentMetadata)
        assert metadata.name == "code_gen"
        assert metadata.agent_class == MockCodeAgent
        assert AgentCapability.CODE_GENERATION in metadata.capabilities
        assert metadata.priority == 10

    def test_get_agent_metadata_nonexistent(self, registry):
        """Test getting metadata for nonexistent agent."""
        with pytest.raises(ValueError, match="not found"):
            registry.get_agent_metadata("nonexistent")

    def test_get_agent_instance(self, populated_registry):
        """Test creating agent instance."""
        agent = populated_registry.get_agent("code_gen")

        assert isinstance(agent, MockCodeAgent)
        assert agent.get_name() == "mock_code_agent"

    def test_find_agents_by_capability(self, populated_registry):
        """Test finding agents by single capability."""
        agents = populated_registry.find_agents_by_capability(
            AgentCapability.CODE_GENERATION
        )

        assert len(agents) == 1
        assert agents[0] == "code_gen"

    def test_find_agents_by_capability_priority_filter(self, populated_registry):
        """Test finding agents by capability with priority filter."""
        agents = populated_registry.find_agents_by_capability(
            AgentCapability.CODE_DOCUMENTATION,
            min_priority=6
        )

        # doc_gen has priority 5, should be filtered out
        assert len(agents) == 0

        agents = populated_registry.find_agents_by_capability(
            AgentCapability.CODE_DOCUMENTATION,
            min_priority=5
        )

        assert len(agents) == 1
        assert agents[0] == "doc_gen"

    def test_find_agents_by_capabilities_match_any(self, populated_registry):
        """Test finding agents by multiple capabilities (match any)."""
        agents = populated_registry.find_agents_by_capabilities(
            capabilities={AgentCapability.CODE_GENERATION, AgentCapability.UNIT_TESTING},
            match_all=False
        )

        assert len(agents) == 2
        assert "code_gen" in agents
        assert "test_gen" in agents
        # Should be sorted by priority
        assert agents[0] == "code_gen"  # priority 10
        assert agents[1] == "test_gen"  # priority 8

    def test_find_agents_by_capabilities_match_all(self, populated_registry):
        """Test finding agents by multiple capabilities (match all)."""
        # Register agent with both capabilities
        populated_registry.register(
            name="multi_agent",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION, AgentCapability.UNIT_TESTING},
            priority=12
        )

        agents = populated_registry.find_agents_by_capabilities(
            capabilities={AgentCapability.CODE_GENERATION, AgentCapability.UNIT_TESTING},
            match_all=True
        )

        assert len(agents) == 1
        assert agents[0] == "multi_agent"

    def test_find_agent_for_task_implementation(self, populated_registry):
        """Test finding agent for implementation task."""
        agent = populated_registry.find_agent_for_task(TaskType.IMPLEMENTATION)

        assert agent == "code_gen"

    def test_find_agent_for_task_testing(self, populated_registry):
        """Test finding agent for testing task."""
        agent = populated_registry.find_agent_for_task(TaskType.TESTING)

        assert agent == "test_gen"

    def test_find_agent_for_task_documentation(self, populated_registry):
        """Test finding agent for documentation task."""
        agent = populated_registry.find_agent_for_task(TaskType.DOCUMENTATION)

        assert agent == "doc_gen"

    def test_find_agent_for_task_priority(self, populated_registry):
        """Test finding agent respects priority."""
        # Register second code agent with higher priority
        populated_registry.register(
            name="code_gen_premium",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION},
            priority=15
        )

        agent = populated_registry.find_agent_for_task(TaskType.IMPLEMENTATION)

        assert agent == "code_gen_premium"

    def test_find_agent_for_task_min_priority(self, populated_registry):
        """Test finding agent with min priority filter."""
        agent = populated_registry.find_agent_for_task(
            TaskType.IMPLEMENTATION,
            min_priority=11
        )

        # code_gen has priority 10, should be filtered out
        assert agent is None

    def test_find_agent_for_task_no_match(self, registry):
        """Test finding agent when no agent can handle task."""
        agent = registry.find_agent_for_task(TaskType.IMPLEMENTATION)

        assert agent is None

    def test_list_agents_all(self, populated_registry):
        """Test listing all agents."""
        agents = populated_registry.list_agents()

        assert len(agents) == 3
        assert "code_gen" in agents
        assert "test_gen" in agents
        assert "doc_gen" in agents

    def test_list_agents_by_task_type(self, populated_registry):
        """Test listing agents by task type."""
        agents = populated_registry.list_agents(task_type=TaskType.IMPLEMENTATION)

        assert len(agents) == 1
        assert "code_gen" in agents

    def test_list_agents_by_capability(self, populated_registry):
        """Test listing agents by capability."""
        agents = populated_registry.list_agents(capability=AgentCapability.CODE_GENERATION)

        assert len(agents) == 1
        assert "code_gen" in agents

    def test_list_agents_by_tags(self, registry):
        """Test listing agents by tags."""
        registry.register(
            name="agent1",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION},
            tags={"python", "backend"}
        )

        registry.register(
            name="agent2",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION},
            tags={"python", "frontend"}
        )

        # Find agents with "python" tag
        agents = registry.list_agents(tags={"python"})
        assert len(agents) == 2

        # Find agents with both "python" and "backend" tags
        agents = registry.list_agents(tags={"python", "backend"})
        assert len(agents) == 1
        assert "agent1" in agents

    def test_get_capability_coverage(self, populated_registry):
        """Test getting capability coverage stats."""
        coverage = populated_registry.get_capability_coverage()

        assert coverage[AgentCapability.CODE_GENERATION] == 1
        assert coverage[AgentCapability.UNIT_TESTING] == 1
        assert coverage[AgentCapability.API_DOCUMENTATION] == 1

    def test_get_task_type_coverage(self, populated_registry):
        """Test getting task type coverage stats."""
        coverage = populated_registry.get_task_type_coverage()

        assert coverage[TaskType.IMPLEMENTATION] == 1
        assert coverage[TaskType.TESTING] == 1
        assert coverage[TaskType.DOCUMENTATION] == 1

    def test_task_capability_map_completeness(self):
        """Test that all task types have capability mappings."""
        for task_type in TaskType:
            assert task_type in TASK_CAPABILITY_MAP
            assert len(TASK_CAPABILITY_MAP[task_type]) > 0

    def test_registry_len(self, populated_registry):
        """Test len() operator."""
        assert len(populated_registry) == 3

    def test_registry_contains(self, populated_registry):
        """Test in operator."""
        assert "code_gen" in populated_registry
        assert "nonexistent" not in populated_registry

    def test_registry_repr(self, populated_registry):
        """Test string representation."""
        repr_str = repr(populated_registry)
        assert "AgentRegistry" in repr_str
        assert "3" in repr_str

    def test_agent_metadata_defaults(self, registry):
        """Test agent metadata default values."""
        registry.register(
            name="test_agent",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION}
        )

        metadata = registry.get_agent_metadata("test_agent")

        assert metadata.priority == 0
        assert metadata.max_concurrent_tasks == 5
        assert metadata.description == ""
        assert metadata.tags == set()

    def test_unregister_updates_indices(self, populated_registry):
        """Test that unregistering updates capability and task indices."""
        # Verify code_gen is in indices
        agents = populated_registry.find_agents_by_capability(AgentCapability.CODE_GENERATION)
        assert "code_gen" in agents

        agents = populated_registry.list_agents(task_type=TaskType.IMPLEMENTATION)
        assert "code_gen" in agents

        # Unregister
        populated_registry.unregister("code_gen")

        # Verify code_gen is removed from indices
        agents = populated_registry.find_agents_by_capability(AgentCapability.CODE_GENERATION)
        assert "code_gen" not in agents

        agents = populated_registry.list_agents(task_type=TaskType.IMPLEMENTATION)
        assert "code_gen" not in agents

    def test_multiple_agents_same_capability(self, registry):
        """Test multiple agents with same capability."""
        registry.register(
            name="agent1",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION},
            priority=10
        )

        registry.register(
            name="agent2",
            agent_class=MockCodeAgent,
            capabilities={AgentCapability.CODE_GENERATION},
            priority=5
        )

        agents = registry.find_agents_by_capability(AgentCapability.CODE_GENERATION)

        assert len(agents) == 2
        # Should be sorted by priority
        assert agents[0] == "agent1"
        assert agents[1] == "agent2"
