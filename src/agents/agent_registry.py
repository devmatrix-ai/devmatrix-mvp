"""
Agent Registry

Manages registration and routing of specialized agents based on their capabilities.
Provides capability-based agent selection for task assignment.
"""

from typing import Dict, List, Set, Optional, Any, Protocol
from dataclasses import dataclass, field
from enum import Enum


class AgentCapability(Enum):
    """Enum of agent capabilities."""
    # Implementation capabilities
    CODE_GENERATION = "code_generation"
    REFACTORING = "refactoring"
    API_DESIGN = "api_design"
    DATABASE_DESIGN = "database_design"

    # Testing capabilities
    UNIT_TESTING = "unit_testing"
    INTEGRATION_TESTING = "integration_testing"
    E2E_TESTING = "e2e_testing"
    PERFORMANCE_TESTING = "performance_testing"

    # Documentation capabilities
    API_DOCUMENTATION = "api_documentation"
    USER_DOCUMENTATION = "user_documentation"
    CODE_DOCUMENTATION = "code_documentation"
    ARCHITECTURE_DOCUMENTATION = "architecture_documentation"

    # Analysis capabilities
    CODE_REVIEW = "code_review"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    ARCHITECTURE_ANALYSIS = "architecture_analysis"


class TaskType(Enum):
    """Enum of task types."""
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    REFACTORING = "refactoring"


# Capability mapping: TaskType -> required capabilities
TASK_CAPABILITY_MAP: Dict[TaskType, List[AgentCapability]] = {
    TaskType.IMPLEMENTATION: [
        AgentCapability.CODE_GENERATION,
        AgentCapability.API_DESIGN
    ],
    TaskType.TESTING: [
        AgentCapability.UNIT_TESTING,
        AgentCapability.INTEGRATION_TESTING
    ],
    TaskType.DOCUMENTATION: [
        AgentCapability.API_DOCUMENTATION,
        AgentCapability.CODE_DOCUMENTATION
    ],
    TaskType.ANALYSIS: [
        AgentCapability.CODE_REVIEW,
        AgentCapability.ARCHITECTURE_ANALYSIS
    ],
    TaskType.REFACTORING: [
        AgentCapability.REFACTORING,
        AgentCapability.CODE_REVIEW
    ]
}


class AgentProtocol(Protocol):
    """Protocol that all agents must implement."""

    def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task.

        Args:
            task: Task dictionary with id, description, type, etc.
            context: Execution context with workspace, dependencies, etc.

        Returns:
            Result dictionary with success status, output, errors
        """
        ...

    def get_capabilities(self) -> Set[AgentCapability]:
        """Return set of agent capabilities."""
        ...

    def get_name(self) -> str:
        """Return agent name."""
        ...


@dataclass
class AgentMetadata:
    """Metadata for registered agents."""
    name: str
    agent_class: type
    capabilities: Set[AgentCapability]
    priority: int = 0  # Higher priority agents are selected first
    max_concurrent_tasks: int = 5
    description: str = ""
    tags: Set[str] = field(default_factory=set)


class AgentRegistry:
    """
    Registry for specialized agents with capability-based routing.

    Manages agent registration, discovery, and task assignment based on
    agent capabilities and task requirements.

    Usage:
        registry = AgentRegistry()

        # Register agents
        registry.register(
            name="code_gen",
            agent_class=CodeGenerationAgent,
            capabilities={AgentCapability.CODE_GENERATION, AgentCapability.API_DESIGN},
            priority=10
        )

        # Find agent for task
        agent = registry.find_agent_for_task(task_type=TaskType.IMPLEMENTATION)

        # Get agent instance
        instance = registry.get_agent("code_gen", api_key="...")
    """

    def __init__(self):
        """Initialize agent registry."""
        self._agents: Dict[str, AgentMetadata] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = {}
        self._task_type_index: Dict[TaskType, Set[str]] = {}

        # Build capability index
        for capability in AgentCapability:
            self._capability_index[capability] = set()

        # Build task type index
        for task_type in TaskType:
            self._task_type_index[task_type] = set()

    def register(
        self,
        name: str,
        agent_class: type,
        capabilities: Set[AgentCapability],
        priority: int = 0,
        max_concurrent_tasks: int = 5,
        description: str = "",
        tags: Optional[Set[str]] = None
    ) -> None:
        """
        Register an agent with the registry.

        Args:
            name: Unique agent name
            agent_class: Agent class (must implement AgentProtocol)
            capabilities: Set of agent capabilities
            priority: Priority for agent selection (higher = preferred)
            max_concurrent_tasks: Maximum concurrent tasks
            description: Agent description
            tags: Optional tags for categorization

        Raises:
            ValueError: If agent name already registered or invalid capabilities
        """
        if name in self._agents:
            raise ValueError(f"Agent '{name}' is already registered")

        if not capabilities:
            raise ValueError(f"Agent '{name}' must have at least one capability")

        # Create metadata
        metadata = AgentMetadata(
            name=name,
            agent_class=agent_class,
            capabilities=capabilities,
            priority=priority,
            max_concurrent_tasks=max_concurrent_tasks,
            description=description,
            tags=tags or set()
        )

        # Register agent
        self._agents[name] = metadata

        # Update capability index
        for capability in capabilities:
            self._capability_index[capability].add(name)

        # Update task type index
        for task_type, required_caps in TASK_CAPABILITY_MAP.items():
            # Agent can handle task if it has any of the required capabilities
            if any(cap in capabilities for cap in required_caps):
                self._task_type_index[task_type].add(name)

    def unregister(self, name: str) -> None:
        """
        Unregister an agent.

        Args:
            name: Agent name to unregister

        Raises:
            ValueError: If agent not found
        """
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found in registry")

        metadata = self._agents[name]

        # Remove from capability index
        for capability in metadata.capabilities:
            self._capability_index[capability].discard(name)

        # Remove from task type index
        for task_type in TaskType:
            self._task_type_index[task_type].discard(name)

        # Remove agent
        del self._agents[name]

    def get_agent_metadata(self, name: str) -> AgentMetadata:
        """
        Get agent metadata.

        Args:
            name: Agent name

        Returns:
            AgentMetadata object

        Raises:
            ValueError: If agent not found
        """
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found in registry")
        return self._agents[name]

    def get_agent(self, name: str, **kwargs) -> Any:
        """
        Create agent instance.

        Args:
            name: Agent name
            **kwargs: Arguments to pass to agent constructor

        Returns:
            Agent instance

        Raises:
            ValueError: If agent not found
        """
        metadata = self.get_agent_metadata(name)
        return metadata.agent_class(**kwargs)

    def find_agents_by_capability(
        self,
        capability: AgentCapability,
        min_priority: int = 0
    ) -> List[str]:
        """
        Find agents with specific capability.

        Args:
            capability: Required capability
            min_priority: Minimum agent priority

        Returns:
            List of agent names, sorted by priority (descending)
        """
        agent_names = self._capability_index.get(capability, set())

        # Filter by priority and sort
        filtered = [
            name for name in agent_names
            if self._agents[name].priority >= min_priority
        ]

        return sorted(
            filtered,
            key=lambda name: self._agents[name].priority,
            reverse=True
        )

    def find_agents_by_capabilities(
        self,
        capabilities: Set[AgentCapability],
        match_all: bool = False,
        min_priority: int = 0
    ) -> List[str]:
        """
        Find agents with multiple capabilities.

        Args:
            capabilities: Required capabilities
            match_all: If True, agent must have all capabilities. If False, any capability.
            min_priority: Minimum agent priority

        Returns:
            List of agent names, sorted by priority (descending)
        """
        if not capabilities:
            return []

        candidate_agents = set(self._agents.keys())

        for capability in capabilities:
            agents_with_cap = self._capability_index.get(capability, set())

            if match_all:
                # Agent must have ALL capabilities
                candidate_agents &= agents_with_cap
            else:
                # Agent must have ANY capability (union on first iteration)
                if capability == next(iter(capabilities)):
                    candidate_agents = agents_with_cap
                else:
                    candidate_agents |= agents_with_cap

        # Filter by priority and sort
        filtered = [
            name for name in candidate_agents
            if self._agents[name].priority >= min_priority
        ]

        return sorted(
            filtered,
            key=lambda name: self._agents[name].priority,
            reverse=True
        )

    def find_agent_for_task(
        self,
        task_type: TaskType,
        task_description: Optional[str] = None,
        min_priority: int = 0
    ) -> Optional[str]:
        """
        Find best agent for task type.

        Args:
            task_type: Type of task
            task_description: Optional task description for additional context
            min_priority: Minimum agent priority

        Returns:
            Agent name or None if no suitable agent found
        """
        agent_names = self._task_type_index.get(task_type, set())

        if not agent_names:
            return None

        # Filter by priority and sort
        filtered = [
            name for name in agent_names
            if self._agents[name].priority >= min_priority
        ]

        if not filtered:
            return None

        # Sort by priority (descending)
        sorted_agents = sorted(
            filtered,
            key=lambda name: self._agents[name].priority,
            reverse=True
        )

        return sorted_agents[0]

    def list_agents(
        self,
        task_type: Optional[TaskType] = None,
        capability: Optional[AgentCapability] = None,
        tags: Optional[Set[str]] = None
    ) -> List[str]:
        """
        List registered agents.

        Args:
            task_type: Optional filter by task type
            capability: Optional filter by capability
            tags: Optional filter by tags

        Returns:
            List of agent names
        """
        agents = set(self._agents.keys())

        # Filter by task type
        if task_type is not None:
            agents &= self._task_type_index.get(task_type, set())

        # Filter by capability
        if capability is not None:
            agents &= self._capability_index.get(capability, set())

        # Filter by tags
        if tags is not None:
            agents = {
                name for name in agents
                if tags.issubset(self._agents[name].tags)
            }

        return sorted(list(agents))

    def get_capability_coverage(self) -> Dict[AgentCapability, int]:
        """
        Get coverage statistics for each capability.

        Returns:
            Dictionary mapping capability to number of agents providing it
        """
        return {
            capability: len(agents)
            for capability, agents in self._capability_index.items()
        }

    def get_task_type_coverage(self) -> Dict[TaskType, int]:
        """
        Get coverage statistics for each task type.

        Returns:
            Dictionary mapping task type to number of agents that can handle it
        """
        return {
            task_type: len(agents)
            for task_type, agents in self._task_type_index.items()
        }

    def __len__(self) -> int:
        """Return number of registered agents."""
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        """Check if agent is registered."""
        return name in self._agents

    def __repr__(self) -> str:
        """String representation."""
        return f"AgentRegistry(agents={len(self._agents)})"
