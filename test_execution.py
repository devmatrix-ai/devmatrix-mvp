#!/usr/bin/env python3
"""
Test script for OrchestratorAgent task execution.
"""

import sys
from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.agent_registry import AgentRegistry, AgentCapability
from src.agents.implementation_agent import ImplementationAgent
from src.agents.testing_agent import TestingAgent
from src.agents.documentation_agent import DocumentationAgent

def main():
    print("=" * 60)
    print("Testing OrchestratorAgent with Task Execution")
    print("=" * 60)

    # Create registry and register agents
    registry = AgentRegistry()

    print("\n📝 Registering agents...")
    registry.register(
        name="ImplementationAgent",
        agent_class=ImplementationAgent,
        capabilities={
            AgentCapability.CODE_GENERATION,
            AgentCapability.API_DESIGN,
            AgentCapability.REFACTORING
        },
        priority=10
    )

    registry.register(
        name="TestingAgent",
        agent_class=TestingAgent,
        capabilities={
            AgentCapability.UNIT_TESTING,
            AgentCapability.INTEGRATION_TESTING
        },
        priority=8
    )

    registry.register(
        name="DocumentationAgent",
        agent_class=DocumentationAgent,
        capabilities={
            AgentCapability.API_DOCUMENTATION,
            AgentCapability.CODE_DOCUMENTATION
        },
        priority=6
    )

    print(f"✓ Registered {len(registry)} agents")

    # Create orchestrator
    print("\n🎯 Creating OrchestratorAgent...")
    orchestrator = OrchestratorAgent(agent_registry=registry)

    # Test with simple project
    print("\n🚀 Testing with simple project...")
    request = "Create a simple calculator function with add and subtract operations"

    print(f"\nRequest: {request}\n")

    result = orchestrator.orchestrate(
        user_request=request,
        workspace_id="test-calculator"
    )

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\n✅ Success: {result['success']}")
    print(f"📊 Project Type: {result['project_type']}")
    print(f"📈 Complexity: {result['complexity']}")
    print(f"📝 Total Tasks: {len(result['tasks'])}")
    print(f"✓ Completed: {len(result.get('completed_tasks', []))}")
    print(f"❌ Failed: {len(result.get('failed_tasks', []))}")

    if result.get('completed_tasks'):
        print("\n✅ Completed Tasks:")
        for task_id in result['completed_tasks']:
            task = next((t for t in result['tasks'] if t['id'] == task_id), None)
            if task:
                print(f"  - {task_id}: {task['description']}")

    if result.get('failed_tasks'):
        print("\n❌ Failed Tasks:")
        for task_id in result['failed_tasks']:
            task = next((t for t in result['tasks'] if t['id'] == task_id), None)
            if task:
                print(f"  - {task_id}: {task['description']}")

    print("\n" + "=" * 60)

    return 0 if result['success'] else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
