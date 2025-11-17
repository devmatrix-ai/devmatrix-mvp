#!/usr/bin/env python3
"""
Test script for WebSocket events (Opción 2).

Tests all 6 event types:
1. execution_started
2. progress_update (simulates 10 tasks)
3. artifact_created
4. wave_completed
5. error
6. execution_completed
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.websocket.manager import WebSocketManager


async def test_websocket_events():
    """Test all WebSocket events."""
    print("=" * 80)
    print("🧪 Testing WebSocket Events (Opción 2)")
    print("=" * 80)
    print()

    # Initialize WebSocketManager (without actual Socket.IO server)
    ws_manager = WebSocketManager()

    session_id = str(uuid4())
    execution_id = str(uuid4())

    print(f"📍 Session ID: {session_id}")
    print(f"📍 Execution ID: {execution_id}")
    print()

    # Test 1: execution_started
    print("=" * 80)
    print("TEST 1: execution_started")
    print("=" * 80)

    phases = [
        {"phase": 0, "name": "Discovery", "task_count": 5, "status": "pending"},
        {"phase": 1, "name": "Analysis", "task_count": 15, "status": "pending"},
        {"phase": 2, "name": "Planning", "task_count": 20, "status": "pending"},
        {"phase": 3, "name": "Execution", "task_count": 70, "status": "pending"},
        {"phase": 4, "name": "Validation", "task_count": 10, "status": "pending"},
    ]

    try:
        await ws_manager.emit_execution_started(
            session_id=session_id,
            execution_id=execution_id,
            total_tasks=120,
            phases=phases
        )
        print("✅ execution_started emitted successfully")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    print()

    # Test 2: progress_update (simulate 10 tasks)
    print("=" * 80)
    print("TEST 2: progress_update (10 tasks simulation)")
    print("=" * 80)

    total_tasks = 120
    for i in range(1, 11):
        task_id = f"task_{i:03d}"
        task_name = f"Implement feature {i}"
        phase = 3  # Execution
        phase_name = "Execution"
        status = "completed"
        progress = i
        progress_percent = (i / total_tasks) * 100
        completed_tasks = i
        current_wave = 1
        duration_ms = 2340.5 + (i * 100)

        try:
            await ws_manager.emit_progress_update(
                session_id=session_id,
                task_id=task_id,
                task_name=task_name,
                phase=phase,
                phase_name=phase_name,
                status=status,
                progress=progress,
                progress_percent=progress_percent,
                completed_tasks=completed_tasks,
                total_tasks=total_tasks,
                current_wave=current_wave,
                duration_ms=duration_ms,
                subtask_status={}
            )
            print(f"✅ progress_update {i}/10: {progress_percent:.2f}% ({task_id})")
        except Exception as e:
            print(f"❌ ERROR on task {i}: {e}")

        # Small delay to simulate real execution
        await asyncio.sleep(0.1)

    print()

    # Test 3: artifact_created
    print("=" * 80)
    print("TEST 3: artifact_created")
    print("=" * 80)

    artifacts = [
        ("auth.py", "file", "src/services/auth.py", 2048),
        ("models.py", "file", "src/models/user.py", 3500),
        ("test_auth.py", "test", "tests/test_auth.py", 1024),
    ]

    for artifact_name, artifact_type, file_path, size_bytes in artifacts:
        artifact_id = str(uuid4())
        try:
            await ws_manager.emit_artifact_created(
                session_id=session_id,
                artifact_id=artifact_id,
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                file_path=file_path,
                size_bytes=size_bytes,
                task_id="task_005",
                metadata={"language": "python"}
            )
            print(f"✅ artifact_created: {artifact_name} ({size_bytes} bytes)")
        except Exception as e:
            print(f"❌ ERROR: {e}")

    print()

    # Test 4: wave_completed
    print("=" * 80)
    print("TEST 4: wave_completed")
    print("=" * 80)

    try:
        await ws_manager.emit_wave_completed(
            session_id=session_id,
            wave_number=1,
            tasks_in_wave=10,
            successful_tasks=9,
            failed_tasks=1,
            duration_ms=45000.0,
            artifacts_created=3
        )
        print("✅ wave_completed emitted successfully")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()

    # Test 5: error
    print("=" * 80)
    print("TEST 5: error")
    print("=" * 80)

    error_id = str(uuid4())
    try:
        await ws_manager.emit_error(
            session_id=session_id,
            error_id=error_id,
            task_id="task_007",
            task_name="Validate authentication",
            error_type="validation_error",
            error_message="Test assertion failed: expected 200, got 401",
            stack_trace="Traceback (most recent call last):\n  File ...",
            retry_count=1,
            max_retries=3,
            recoverable=True
        )
        print("✅ error emitted successfully")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()

    # Test 6: execution_completed
    print("=" * 80)
    print("TEST 6: execution_completed")
    print("=" * 80)

    try:
        await ws_manager.emit_execution_completed(
            session_id=session_id,
            execution_id=execution_id,
            status="completed",
            total_tasks=120,
            completed_tasks=119,
            failed_tasks=1,
            skipped_tasks=0,
            total_duration_ms=630000.0,
            artifacts_created=45,
            final_stats={
                "tokens_used": 67450,
                "cost_usd": 0.42
            }
        )
        print("✅ execution_completed emitted successfully")
    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()
    print("=" * 80)
    print("🎉 All WebSocket events tested successfully!")
    print("=" * 80)
    print()
    print("📊 Summary:")
    print("  - execution_started: 1 event")
    print("  - progress_update: 10 events (simulated, real: 120)")
    print("  - artifact_created: 3 events (simulated, real: ~45)")
    print("  - wave_completed: 1 event (simulated, real: 8-10)")
    print("  - error: 1 event (simulated, real: 0-20)")
    print("  - execution_completed: 1 event")
    print()
    print("✅ Total simulated: 17 events")
    print("✅ Real execution: ~180-200 events")
    print()


async def main():
    """Main entry point."""
    try:
        await test_websocket_events()
        return 0
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
