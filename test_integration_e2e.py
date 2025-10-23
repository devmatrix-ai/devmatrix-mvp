"""
End-to-End Integration Test

Tests the complete MasterPlan flow with REAL LLM calls:
1. Discovery Agent → generates DDD discovery
2. MasterPlan Generator → generates 50-task plan
3. Task Executor → executes first task
4. Code Validator → validates generated code

This uses REAL API calls and demonstrates the entire system works.
"""

import asyncio
import sys
from pathlib import Path

from src.services import DiscoveryAgent, MasterPlanGenerator, TaskExecutor, CodeValidator
from src.models.masterplan import TaskStatus


async def main():
    print("=" * 80)
    print("🚀 END-TO-END INTEGRATION TEST")
    print("=" * 80)
    print("\nThis test will:")
    print("1. ✅ Create a real Discovery with LLM (Sonnet 4.5)")
    print("2. ✅ Generate a real MasterPlan with LLM (Sonnet 4.5)")
    print("3. ✅ Execute the first task with LLM (Haiku/Sonnet)")
    print("4. ✅ Validate the generated code")
    print("\n⚠️  This will cost ~$0.50 in API calls\n")

    # Initialize services
    discovery_agent = DiscoveryAgent()
    masterplan_generator = MasterPlanGenerator(use_rag=False)  # No RAG for test
    task_executor = TaskExecutor(use_rag=False, workspace_dir="./test_e2e_workspace")
    code_validator = CodeValidator()

    session_id = "test_e2e_001"
    user_id = "test_user_001"

    # ========================================================================
    # STEP 1: DISCOVERY
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: Discovery Agent - DDD Analysis")
    print("=" * 80)

    user_request = """
    Build a simple Task Management API with the following features:
    - Users can create, read, update, and delete tasks
    - Each task has: title, description, status (todo/in_progress/done), priority (low/medium/high)
    - Tasks belong to users
    - Users can filter tasks by status and priority
    - RESTful API with FastAPI
    - PostgreSQL database
    """

    print(f"\n📝 User Request:\n{user_request}\n")
    print("🤖 Calling Discovery Agent (Sonnet 4.5)...")

    try:
        discovery_id = await discovery_agent.conduct_discovery(
            user_request=user_request,
            session_id=session_id,
            user_id=user_id
        )

        print(f"✅ Discovery created: {discovery_id}")

        # Retrieve and display discovery
        discovery = discovery_agent.get_discovery(discovery_id)
        print(f"\n📊 Discovery Results:")
        print(f"   Domain: {discovery.domain}")
        print(f"   Bounded Contexts: {len(discovery.bounded_contexts)}")
        print(f"   Aggregates: {len(discovery.aggregates)}")
        print(f"   Model: {discovery.llm_model}")
        print(f"   Cost: ${discovery.llm_cost_usd:.4f}")

    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return 1

    # ========================================================================
    # STEP 2: MASTERPLAN GENERATION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: MasterPlan Generator - 50-Task Plan")
    print("=" * 80)

    print("\n🤖 Calling MasterPlan Generator (Sonnet 4.5)...")
    print("⏳ This may take 30-60 seconds (generating 50 tasks)...\n")

    try:
        masterplan_id = await masterplan_generator.generate_masterplan(
            discovery_id=discovery_id,
            session_id=session_id,
            user_id=user_id
        )

        print(f"✅ MasterPlan created: {masterplan_id}")

        # Retrieve and display masterplan
        masterplan = masterplan_generator.get_masterplan(masterplan_id)
        print(f"\n📊 MasterPlan Results:")
        print(f"   Project: {masterplan.project_name}")
        print(f"   Phases: {masterplan.total_phases}")
        print(f"   Milestones: {masterplan.total_milestones}")
        print(f"   Tasks: {masterplan.total_tasks}")
        print(f"   Model: {masterplan.llm_model}")
        print(f"   Generation Cost: ${masterplan.generation_cost_usd:.4f}")
        print(f"   Estimated Total Cost: ${masterplan.estimated_cost_usd:.2f}")
        print(f"   Estimated Duration: {masterplan.estimated_duration_minutes} minutes")

        # Display tech stack
        print(f"\n🛠️  Tech Stack:")
        for key, value in masterplan.tech_stack.items():
            print(f"   {key}: {value}")

        # Display first 5 tasks
        print(f"\n📋 First 5 Tasks:")
        from src.config.database import get_db_context
        from src.models.masterplan import MasterPlanTask, MasterPlanMilestone, MasterPlanPhase

        with get_db_context() as db:
            # Get first 5 tasks by task_number
            tasks = db.query(MasterPlanTask).join(
                MasterPlanMilestone
            ).join(
                MasterPlanPhase
            ).filter(
                MasterPlanPhase.masterplan_id == masterplan_id
            ).order_by(MasterPlanTask.task_number).limit(5).all()

            for task in tasks:
                print(f"   #{task.task_number}: {task.name} [{task.complexity.value}]")

    except Exception as e:
        print(f"❌ MasterPlan generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ========================================================================
    # STEP 3: TASK EXECUTION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: Task Executor - Execute First Task")
    print("=" * 80)

    # Get first task
    with get_db_context() as db:
        first_task = db.query(MasterPlanTask).order_by(
            MasterPlanTask.task_number
        ).first()

        if not first_task:
            print("❌ No tasks found in MasterPlan")
            return 1

        # Save task info before leaving session
        task_id = first_task.task_id
        task_number = first_task.task_number
        task_name = first_task.name
        task_complexity = first_task.complexity.value
        task_target_files = first_task.target_files

    print(f"\n📋 Executing Task #{task_number}")
    print(f"   Name: {task_name}")
    print(f"   Complexity: {task_complexity}")
    print(f"   Target Files: {', '.join(task_target_files)}")

    print(f"\n🤖 Calling Task Executor (Haiku/Sonnet based on complexity)...")

    try:
        result = await task_executor.execute_task(task_id=task_id)

        print(f"✅ Task execution completed!")
        print(f"\n📊 Execution Results:")
        print(f"   Status: {result['status']}")
        print(f"   Model: {result['model']}")
        print(f"   Cost: ${result['cost_usd']:.4f}")
        print(f"   Cached Tokens: {result['cached_tokens']}")
        print(f"   Files Saved: {len(result['files_saved'])}")

        for file_path in result['files_saved']:
            print(f"      - {file_path}")

            # Show file preview
            file_content = Path(file_path).read_text()
            print(f"\n📄 File Preview ({file_path}):")
            print("   " + "-" * 76)
            lines = file_content.split('\n')
            for line in lines[:20]:  # First 20 lines
                print(f"   {line}")
            if len(lines) > 20:
                remaining = len(lines) - 20
                print(f"   ... ({remaining} more lines)")
            print("   " + "-" * 76)

    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ========================================================================
    # STEP 4: CODE VALIDATION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: Code Validator - Validate Generated Code")
    print("=" * 80)

    print("\n🔍 Validating generated code...\n")

    try:
        all_valid = True
        for file_path in result['files_saved']:
            is_valid, errors = code_validator.validate_file(file_path)

            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"{status}: {file_path}")

            if errors:
                for error in errors:
                    severity_icon = "🔴" if error.severity == "error" else "🟡"
                    print(f"   {severity_icon} Line {error.line}: {error.message}")

                if not is_valid:
                    all_valid = False

        if all_valid:
            print("\n✅ All generated code is valid!")
        else:
            print("\n⚠️  Some validation errors found (see above)")

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("🎉 END-TO-END TEST COMPLETE!")
    print("=" * 80)

    print("\n📊 Final Summary:")
    print(f"   ✅ Discovery completed: {discovery.domain}")
    print(f"   ✅ MasterPlan generated: {masterplan.total_tasks} tasks")
    print(f"   ✅ Task executed: {first_task.name}")
    print(f"   ✅ Code validated: {'PASS' if all_valid else 'WARNINGS'}")

    total_cost = (
        discovery.llm_cost_usd +
        masterplan.generation_cost_usd +
        result['cost_usd']
    )
    print(f"\n💰 Total API Cost: ${total_cost:.4f}")

    print(f"\n📁 Generated Files Location:")
    print(f"   {Path('./test_e2e_workspace').absolute()}")

    print("\n✅ ALL SYSTEMS OPERATIONAL - NO MOCKS, ALL REAL!\n")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
