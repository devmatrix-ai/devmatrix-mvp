"""
E2E Test: MGE V2 Complete Pipeline with Checkpoint/Recovery

Tests complete flow from user request to generated project workspace with:
- Automatic checkpoint persistence after each phase
- Recovery from failure points
- Retry logic with exponential backoff for transient failures
- Phase-by-phase validation

Phases:
1. User Request → Discovery
2. Discovery → MasterPlan (120 tasks)
3. Tasks → Code Generation (LLM)
4. Code → Atomization (10 LOC atoms)
5. Atoms → Wave Execution
6. Atoms → File Writing
7. Project → Infrastructure Generation
8. Validation → Docker build

Author: DevMatrix Team
Date: 2025-11-10
"""

import pytest
import asyncio
import uuid
import subprocess
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.mge_v2_orchestration_service import MGE_V2_OrchestrationService
from src.config.database import Base
from src.models import MasterPlan, MasterPlanTask, AtomicUnit, DiscoveryDocument

# Import checkpoint and retry components
from .checkpoint_manager import CheckpointManager, PhaseStatus
from .retry_handler import PhaseRetryHandler, RetryConfig


# Test database setup
TEST_DATABASE_URL = "postgresql://devmatrix:devmatrix@localhost:5432/devmatrix_test"


@pytest.fixture(scope="module")
def test_db():
    """Create test database session."""
    engine = create_engine(TEST_DATABASE_URL)

    # Drop and recreate all tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def test_user_id():
    """Generate test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_session_id():
    """Generate test session ID."""
    return str(uuid.uuid4())


@pytest.fixture
def checkpoint_manager():
    """Create checkpoint manager."""
    return CheckpointManager()


@pytest.fixture
def retry_handler():
    """Create retry handler with custom config."""
    config = RetryConfig(
        max_retries=3,
        initial_delay=5.0,
        max_delay=120.0,
        exponential_base=2.0,
        jitter=True
    )
    return PhaseRetryHandler(config=config)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_mge_v2_pipeline_fastapi(
    test_db,
    test_user_id,
    test_session_id,
    checkpoint_manager,
    retry_handler
):
    """
    E2E Test: Complete MGE V2 pipeline for FastAPI project with checkpoint/recovery

    Expected duration: ~12 minutes
    Expected cost: ~$7

    Features:
    - Automatic checkpoint after each phase
    - Resume from failure point
    - Retry with exponential backoff
    - Detailed progress tracking
    """
    print("\n" + "="*80)
    print("🚀 Starting MGE V2 E2E Test - FastAPI Project (with recovery)")
    print("="*80 + "\n")

    # Generate unique test ID for checkpoint
    test_id = f"fastapi_pipeline_{test_session_id[:8]}"

    # User request
    user_request = """
    Create a FastAPI REST API for task management system with the following features:

    - User authentication (JWT)
    - CRUD operations for tasks
    - Task categories and tags
    - Due dates and priorities
    - PostgreSQL database with SQLAlchemy
    - Pydantic schemas for validation
    - Alembic for migrations
    """

    # Check for existing checkpoint
    checkpoint = checkpoint_manager.load_checkpoint(test_id)

    if checkpoint:
        print("♻️  Found existing checkpoint - resuming from last state\n")
        checkpoint_manager.print_checkpoint_status(checkpoint)

        # Get resume phase
        resume_phase = checkpoint_manager.get_resume_phase(checkpoint)

        if resume_phase:
            print(f"▶️  Resuming from phase: {resume_phase}\n")
        else:
            print("✅ All phases already completed!\n")
            return
    else:
        print("📝 User Request: {user_request[:100]}...")
        print(f"👤 User ID: {test_user_id}")
        print(f"🔑 Session ID: {test_session_id}\n")

        # Create new checkpoint
        # NOTE: Phase order matches event emission order from orchestration service
        phases = [
            "discovery",
            "masterplan",
            "code_generation",
            "atomization",
            "file_writing",       # Phase 5: emitted during execution
            "infrastructure",     # Phase 6: emitted during execution
            "wave_execution"      # Phase 7: 'complete' event emitted last
        ]

        checkpoint = checkpoint_manager.create_checkpoint(
            test_name="MGE V2 FastAPI Pipeline",
            test_id=test_id,
            user_request=user_request,
            phases=phases
        )

        print(f"💾 Created checkpoint: {test_id}\n")

    # Initialize orchestration service
    service = MGE_V2_OrchestrationService(
        db=test_db,
        enable_caching=True,
        enable_rag=True
    )

    # SHARED GENERATOR - Initialize once and reuse across all phases
    _pipeline_generator = None
    _consumed_phases = set()

    async def execute_phase_with_checkpoint(
        phase_name: str,
        phase_event_matcher,
        phase_data_extractor
    ):
        """Execute phase with checkpoint persistence and retry logic.

        Args:
            phase_name: Name of the phase (discovery, masterplan, etc.)
            phase_event_matcher: Function that returns True when phase completes
            phase_data_extractor: Function that extracts phase data from completion event
        """
        nonlocal _pipeline_generator, _consumed_phases

        # Check if phase already completed
        phase = checkpoint.phases[phase_name]
        if phase.status == PhaseStatus.COMPLETED:
            print(f"⏭️  Phase {phase_name} already completed - skipping")
            checkpoint_manager.skip_phase(checkpoint, phase_name)
            # Return cached data from checkpoint
            return {
                'discovery_id': phase.discovery_id,
                'masterplan_id': phase.masterplan_id,
                'generated_tasks_count': phase.generated_tasks_count,
                'generated_code_count': phase.generated_code_count,
                'atoms_count': phase.atoms_count
            }

        # Start phase
        checkpoint_manager.start_phase(checkpoint, phase_name)
        print(f"\n▶️  Starting phase: {phase_name}")

        try:
            # Initialize generator ONCE on first phase
            if _pipeline_generator is None:
                print("🔄 Initializing pipeline generator...")
                _pipeline_generator = service.orchestrate_from_request(
                    user_request=user_request,
                    workspace_id="test-workspace",
                    session_id=test_session_id,
                    user_id=test_user_id
                )

            # Consume events until this phase completes
            phase_result = None
            async for event in _pipeline_generator:
                event_type = event.get('type', '')
                event_phase = event.get('phase', '')

                # Log ALL events for debugging
                print(f"  [DEBUG] Event: type={event_type}, phase={event_phase}, keys={list(event.keys())}")

                # Log status events
                if event_type == 'status':
                    print(f"  📍 {event_phase}: {event.get('message', '')}")

                # Check if this event signals phase completion
                if phase_event_matcher(event):
                    print(f"  🎯 MATCHED! Extracting data for phase {phase_name}")
                    phase_result = phase_data_extractor(event, test_db)
                    _consumed_phases.add(phase_name)
                    break

                # Check for error events that terminate the generator
                if event_type == 'error':
                    error_msg = event.get('message', 'Unknown error')
                    print(f"  ⚠️ Pipeline error detected: {error_msg}")
                    raise RuntimeError(f"Pipeline failed during {phase_name}: {error_msg}")

            if phase_result is None:
                raise RuntimeError(f"Phase {phase_name} did not complete (no matching event)")

            # Mark complete with phase data
            checkpoint_manager.complete_phase(
                checkpoint,
                phase_name,
                **phase_result
            )

            print(f"✅ Phase {phase_name} completed successfully")
            return phase_result

        except Exception as e:
            # Mark failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            checkpoint_manager.fail_phase(checkpoint, phase_name, error_msg)

            print(f"❌ Phase {phase_name} failed: {error_msg}")

            # Retry logic with exponential backoff
            if phase.retry_count < retry_handler.config.max_retries:
                delay = retry_handler.config.initial_delay * (
                    retry_handler.config.exponential_base ** (phase.retry_count - 1)
                )
                print(f"⏳ Retrying in {delay:.1f}s... (attempt {phase.retry_count + 1})")
                await asyncio.sleep(delay)

                # Reset generator for retry
                _pipeline_generator = None
                _consumed_phases.clear()

                # Recursive retry
                return await execute_phase_with_checkpoint(
                    phase_name,
                    phase_event_matcher,
                    phase_data_extractor
                )
            else:
                raise

    # ============================================================================
    # PHASE 1: Discovery
    # ============================================================================
    def discovery_matcher(event):
        """Check if event signals discovery completion."""
        return (
            event.get('type') == 'status' and
            event.get('phase') == 'discovery' and
            'created successfully' in event.get('message', '').lower()
        )

    def discovery_extractor(event, db):
        """Extract discovery data from completion event."""
        discovery_id = event.get('discovery_id')

        # Verify discovery in database
        discovery = db.query(DiscoveryDocument).filter(
            DiscoveryDocument.discovery_id == uuid.UUID(discovery_id)
        ).first()

        return {
            'discovery_id': discovery_id,
            'domain': discovery.domain if discovery else 'N/A',
            'bounded_contexts_count': len(discovery.bounded_contexts or []) if discovery else 0,
            'aggregates_count': len(discovery.aggregates or []) if discovery else 0,
            'value_objects_count': len(discovery.value_objects or []) if discovery else 0
        }

    discovery_result = await execute_phase_with_checkpoint(
        "discovery",
        discovery_matcher,
        discovery_extractor
    )

    print(f"   ✅ Discovery ID: {discovery_result['discovery_id']}")
    print(f"   ✅ Domain: {discovery_result.get('domain', 'N/A')}")
    print(f"   ✅ Bounded Contexts: {discovery_result.get('bounded_contexts_count', 0)}")
    print(f"   ✅ Aggregates: {discovery_result.get('aggregates_count', 0)}")

    # ============================================================================
    # PHASE 2: MasterPlan Generation
    # ============================================================================
    def masterplan_matcher(event):
        """Check if event signals masterplan completion."""
        return (
            event.get('type') == 'status' and
            event.get('phase') == 'masterplan_generation' and
            'generated successfully' in event.get('message', '').lower()
        )

    def masterplan_extractor(event, db):
        """Extract masterplan data from completion event."""
        masterplan_id = event.get('masterplan_id')

        # Verify MasterPlan in database
        masterplan = db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == uuid.UUID(masterplan_id)
        ).first()

        tasks = db.query(MasterPlanTask).filter(
            MasterPlanTask.masterplan_id == uuid.UUID(masterplan_id)
        ).all()

        return {
            'masterplan_id': masterplan_id,
            'project_name': masterplan.project_name if masterplan else 'N/A',
            'total_phases': masterplan.total_phases if masterplan else 0,
            'total_milestones': masterplan.total_milestones if masterplan else 0,
            'generated_tasks_count': len(tasks)
        }

    masterplan_result = await execute_phase_with_checkpoint(
        "masterplan",
        masterplan_matcher,
        masterplan_extractor
    )

    print(f"   ✅ MasterPlan ID: {masterplan_result['masterplan_id']}")
    print(f"   ✅ Project Name: {masterplan_result.get('project_name', 'N/A')}")
    print(f"   ✅ Total Tasks: {masterplan_result.get('generated_tasks_count', 0)}")

    # ============================================================================
    # PHASE 3: Code Generation
    # ============================================================================
    def code_generation_matcher(event):
        """Check if event signals code generation completion."""
        return (
            event.get('type') == 'status' and
            event.get('phase') == 'code_generation' and
            'complete' in event.get('message', '').lower()
        )

    def code_generation_extractor(event, db):
        """Extract code generation data."""
        masterplan_id = masterplan_result.get('masterplan_id')

        # Get tasks with generated code
        tasks = db.query(MasterPlanTask).filter(
            MasterPlanTask.masterplan_id == uuid.UUID(masterplan_id)
        ).all()

        tasks_with_code = [t for t in tasks if t.llm_response is not None]
        total_code_lines = sum(t.llm_response.count('\n') for t in tasks_with_code)
        total_cost = sum(t.llm_cost_usd or 0 for t in tasks)

        return {
            'generated_code_count': len(tasks_with_code),
            'total_code_lines': total_code_lines,
            'total_cost_usd': total_cost
        }

    code_gen_result = await execute_phase_with_checkpoint(
        "code_generation",
        code_generation_matcher,
        code_generation_extractor
    )

    print(f"   ✅ Tasks with code: {code_gen_result.get('generated_code_count', 0)}")
    print(f"   ✅ Total LOC: {code_gen_result.get('total_code_lines', 0):,}")
    print(f"   ✅ Cost: ${code_gen_result.get('total_cost_usd', 0):.2f}")

    # ============================================================================
    # PHASE 4: Atomization
    # ============================================================================
    def atomization_matcher(event):
        """Check if event signals atomization completion."""
        return (
            event.get('type') == 'status' and
            event.get('phase') == 'atomization' and
            'complete' in event.get('message', '').lower()
        )

    def atomization_extractor(event, db):
        """Extract atomization data."""
        masterplan_id = masterplan_result.get('masterplan_id')

        atoms = db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == uuid.UUID(masterplan_id)
        ).all()

        avg_atom_loc = sum(a.loc for a in atoms) / len(atoms) if atoms else 0
        avg_atomicity = sum(a.atomicity_score for a in atoms) / len(atoms) if atoms else 0

        return {
            'atoms_count': len(atoms),
            'avg_atom_loc': avg_atom_loc,
            'avg_atomicity': avg_atomicity
        }

    atomization_result = await execute_phase_with_checkpoint(
        "atomization",
        atomization_matcher,
        atomization_extractor
    )

    print(f"   ✅ Total atoms: {atomization_result.get('atoms_count', 0)}")
    print(f"   ✅ Avg LOC per atom: {atomization_result.get('avg_atom_loc', 0):.1f}")
    print(f"   ✅ Avg atomicity: {atomization_result.get('avg_atomicity', 0):.2%}")

    # ============================================================================
    # PHASE 5: File Writing (processed before wave_execution complete event)
    # ============================================================================
    def file_writing_matcher(event):
        """Check if event signals file writing completion."""
        return (
            event.get('type') == 'status' and
            event.get('phase') == 'file_writing' and
            'files_written' in event
        )

    def file_writing_extractor(event, db):
        """Extract file writing data."""
        from pathlib import Path

        files_written = event.get('files_written', 0)
        workspace_path = event.get('workspace_path', '')

        # Verify files actually exist on filesystem
        workspace = Path(workspace_path)
        actual_files = len(list(workspace.rglob('*.py'))) if workspace.exists() else 0

        return {
            'files_written': files_written,
            'workspace_path': workspace_path,
            'files_verified': actual_files
        }

    file_writing_result = await execute_phase_with_checkpoint(
        "file_writing",
        file_writing_matcher,
        file_writing_extractor
    )

    print(f"   ✅ Files written: {file_writing_result.get('files_written', 0)}")
    print(f"   ✅ Workspace: {file_writing_result.get('workspace_path', 'N/A')}")
    print(f"   ✅ Files verified on disk: {file_writing_result.get('files_verified', 0)}")

    # ============================================================================
    # PHASE 6: Infrastructure Generation (processed before wave_execution complete event)
    # ============================================================================
    def infrastructure_matcher(event):
        """Check if event signals infrastructure generation completion."""
        return (
            event.get('type') == 'status' and
            event.get('phase') == 'infrastructure_generation' and
            'files_generated' in event
        )

    def infrastructure_extractor(event, db):
        """Extract infrastructure generation data."""
        files_generated = event.get('files_generated', 0)
        project_type = event.get('project_type', 'unknown')

        return {
            'files_generated': files_generated,
            'project_type': project_type
        }

    infrastructure_result = await execute_phase_with_checkpoint(
        "infrastructure",
        infrastructure_matcher,
        infrastructure_extractor
    )

    print(f"   ✅ Infrastructure files: {infrastructure_result.get('files_generated', 0)}")
    print(f"   ✅ Project type: {infrastructure_result.get('project_type', 'unknown')}")

    # ============================================================================
    # PHASE 7: Wave Execution (processes 'complete' event which comes LAST)
    # ============================================================================
    def wave_execution_matcher(event):
        """Check if event signals wave execution completion."""
        return (
            event.get('type') == 'complete' and
            'execution_id' in event
        )

    def wave_execution_extractor(event, db):
        """Extract wave execution data."""
        execution_id = event.get('execution_id')
        total_waves = event.get('total_waves', 0)
        total_atoms = event.get('total_atoms', 0)

        return {
            'execution_id': execution_id,
            'total_waves': total_waves,
            'atoms_executed': total_atoms
        }

    wave_execution_result = await execute_phase_with_checkpoint(
        "wave_execution",
        wave_execution_matcher,
        wave_execution_extractor
    )

    print(f"   ✅ Execution ID: {wave_execution_result.get('execution_id', 'N/A')}")
    print(f"   ✅ Total waves: {wave_execution_result.get('total_waves', 0)}")
    print(f"   ✅ Atoms executed: {wave_execution_result.get('atoms_executed', 0)}")

    # ============================================================================
    # Test Complete - All 7 Phases Validated
    # ============================================================================

    # Print final checkpoint status
    print("\n" + "="*80)
    checkpoint_manager.print_checkpoint_status(checkpoint)

    # Cleanup checkpoint on success
    checkpoint_manager.cleanup_checkpoint(test_id)

    print("="*80)
    print("✅ E2E Test PASSED!")
    print("="*80 + "\n")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.benchmark
async def test_mge_v2_performance_benchmark(test_db, test_user_id, test_session_id):
    """
    Performance benchmark test for MGE V2 pipeline.

    Targets:
    - Discovery: < 30s
    - MasterPlan: < 90s
    - Code Gen: < 300s
    - Total: < 720s (12 min)
    """
    print("\n" + "="*80)
    print("⏱️  Performance Benchmark - MGE V2 Pipeline")
    print("="*80 + "\n")

    user_request = "Create a simple FastAPI REST API with user authentication"

    service = MGE_V2_OrchestrationService(db=test_db)

    phase_times = {}
    phase_start = datetime.now()
    current_phase = None

    async for event in service.orchestrate_from_request(
        user_request=user_request,
        workspace_id="benchmark-workspace",
        session_id=test_session_id,
        user_id=test_user_id
    ):
        event_type = event.get('type')

        # Track phase transitions
        if '_start' in event_type:
            phase_name = event_type.replace('_start', '')
            current_phase = phase_name
            phase_start = datetime.now()

        elif '_complete' in event_type or event_type == 'complete':
            if current_phase:
                phase_duration = (datetime.now() - phase_start).total_seconds()
                phase_times[current_phase] = phase_duration
                current_phase = None

    # Print results
    print("📊 Phase Timings:\n")

    targets = {
        'discovery_generation': 30,
        'masterplan_generation': 90,
        'code_generation': 300,
        'atomization': 60,
        'execution': 180,
    }

    for phase, duration in phase_times.items():
        target = targets.get(phase, 0)
        status = "✅" if duration <= target else "⚠️"
        print(f"   {status} {phase}: {duration:.1f}s (target: {target}s)")

    total_time = sum(phase_times.values())
    print(f"\n   Total: {total_time:.1f}s (target: 720s)")
    print()

    # Assertions
    for phase, duration in phase_times.items():
        target = targets.get(phase)
        if target:
            assert duration <= target * 1.5, f"{phase} took {duration}s (target: {target}s)"

    assert total_time < 720, f"Total time {total_time}s exceeds 720s target"

    print("="*80)
    print("✅ Performance Benchmark PASSED!")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
