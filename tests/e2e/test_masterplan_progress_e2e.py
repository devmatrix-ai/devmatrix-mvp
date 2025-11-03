"""
End-to-End Test for MasterPlan Progress UI

Tests the complete flow with real-time progress updates:
1. User sends /masterplan command via chat
2. Backend emits WebSocket events during generation
3. Frontend displays progress indicator in real-time
4. User sees completed MasterPlan

This is a MANUAL test - requires:
- Backend running (with WebSocket support)
- Frontend running (React UI)
- PostgreSQL running
- Valid ANTHROPIC_API_KEY

Run this to verify all services can import correctly:
  python3 -c "from src.services import DiscoveryAgent, MasterPlanGenerator; from src.websocket import WebSocketManager; print('✅ All imports successful')"

Then run the actual test by:
1. Start backend: cd src/api && uvicorn main:app --reload
2. Start frontend: cd src/ui && npm run dev
3. Open browser to http://localhost:5173
4. Type in chat: /masterplan Build a simple Task Management API with CRUD operations
5. Watch the progress indicator appear and update every 5 seconds
6. Verify all components work as expected

Manual Verification Checklist:
[ ] Backend starts without errors
[ ] Frontend connects to WebSocket
[ ] Progress indicator appears when /masterplan command is sent
[ ] Token counter updates every 5 seconds
[ ] Phase text changes ("Generando tareas (1-15)...", etc.)
[ ] Entity counters (Fases, Milestones, Tareas) update
[ ] Progress bar advances smoothly
[ ] Timeline status items change from pending → in_progress → done
[ ] Validation and saving phases are shown
[ ] Completion message appears with confetti 🎉
[ ] Progress indicator disappears after 3 seconds
[ ] Final MasterPlan summary is displayed in chat

Expected Timeline (90 seconds):
t=0s   : User types /masterplan command
t=1s   : Progress indicator appears "Iniciando generación..."
t=5s   : First progress update (5%, "Analizando Discovery Document...")
t=10s  : Second update (10%, "Generando estructura del plan...")
t=15s  : Third update (15%, "Creando fases del proyecto...")
...
t=85s  : Progress reaches 85% ("Optimizando dependencias...")
t=90s  : "Parsing completado" - counters show 3/3, 17/17, 50/50
t=92s  : "Validando dependencias..."
t=94s  : "Guardando en base de datos..."
t=96s  : Progress complete! 🎉
t=99s  : Progress indicator fades out
t=100s : Chat shows final MasterPlan summary

"""

import sys
import asyncio
from pathlib import Path

# Verify imports work
def test_imports():
    """Test that all necessary services can be imported."""
    print("=" * 80)
    print("Testing Service Imports")
    print("=" * 80)

    try:
        print("\n1. Testing DiscoveryAgent import...")
        from src.services import DiscoveryAgent
        print("   ✅ DiscoveryAgent")

        print("\n2. Testing MasterPlanGenerator import...")
        from src.services import MasterPlanGenerator
        print("   ✅ MasterPlanGenerator")

        print("\n3. Testing WebSocketManager import...")
        from src.websocket import WebSocketManager
        print("   ✅ WebSocketManager")

        print("\n4. Testing database connection...")
        from src.config.database import get_db_context
        from sqlalchemy import text
        with get_db_context() as db:
            # Simple query to test connection
            result = db.execute(text("SELECT 1")).scalar()
            assert result == 1
        print("   ✅ PostgreSQL connection")

        print("\n5. Testing LLM client...")
        from src.llm import EnhancedAnthropicClient
        client = EnhancedAnthropicClient()
        print("   ✅ LLM client initialized")

        print("\n" + "=" * 80)
        print("✅ ALL IMPORTS SUCCESSFUL - System Ready!")
        print("=" * 80)
        return True

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ IMPORT FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


async def test_masterplan_generation_programmatic():
    """
    Programmatic test that actually generates a MasterPlan.

    This is NOT the UI test - this just verifies the backend works.
    For UI testing, use the manual checklist above.
    """
    print("\n" + "=" * 80)
    print("Programmatic Backend Test (NO UI)")
    print("=" * 80)
    print("\nThis test will generate a REAL MasterPlan using the backend services.")
    print("⚠️  This will cost ~$0.20 in API calls")
    print()

    response = input("Continue with backend test? (y/N): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return

    try:
        from src.services import DiscoveryAgent, MasterPlanGenerator
        from src.websocket import WebSocketManager
        import socketio

        # Create a mock WebSocket manager (no actual socket)
        print("\n1. Creating mock WebSocket manager...")
        sio = socketio.AsyncServer(async_mode='asgi')
        ws_manager = WebSocketManager(sio)
        print("   ✅ WebSocket manager created")

        # STEP 1: Discovery
        print("\n2. Running Discovery Agent...")
        discovery_agent = DiscoveryAgent()

        discovery_id = await discovery_agent.conduct_discovery(
            user_request="Build a simple Task Management API with CRUD operations for tasks",
            session_id="test_session_progress",
            user_id="test_user"
        )

        discovery = discovery_agent.get_discovery(discovery_id)
        print(f"   ✅ Discovery completed: {discovery.domain}")
        print(f"      Bounded Contexts: {len(discovery.bounded_contexts)}")
        print(f"      Cost: ${discovery.llm_cost_usd:.4f}")

        # STEP 2: MasterPlan
        print("\n3. Running MasterPlan Generator (this will take ~90 seconds)...")
        print("   WebSocket events would be emitted here in real app")
        print("   Progress simulation:")

        masterplan_generator = MasterPlanGenerator(
            use_rag=False,
            websocket_manager=ws_manager  # Mock manager won't actually emit
        )

        masterplan_id = await masterplan_generator.generate_masterplan(
            discovery_id=discovery_id,
            session_id="test_session_progress",
            user_id="test_user"
        )

        masterplan = masterplan_generator.get_masterplan(masterplan_id)

        print(f"\n   ✅ MasterPlan generated!")
        print(f"      Project: {masterplan.project_name}")
        print(f"      Phases: {masterplan.total_phases}")
        print(f"      Milestones: {masterplan.total_milestones}")
        print(f"      Tasks: {masterplan.total_tasks}")
        print(f"      Cost: ${masterplan.generation_cost_usd:.4f}")

        print("\n" + "=" * 80)
        print("✅ BACKEND TEST PASSED")
        print("=" * 80)

        # Cleanup
        print("\nCleaning up test data...")
        from src.config.database import get_db_context
        from src.models.masterplan import MasterPlan, DiscoveryDocument

        with get_db_context() as db:
            db.query(MasterPlan).filter(MasterPlan.masterplan_id == masterplan_id).delete()
            db.query(DiscoveryDocument).filter(DiscoveryDocument.discovery_id == discovery_id).delete()
            db.commit()
        print("✅ Cleanup complete")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """Main test entry point."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║         MasterPlan Progress UI - End-to-End Test Suite                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

This test suite verifies the complete MasterPlan generation flow with
real-time progress updates.

TEST 1: Import Verification (automatic)
TEST 2: Backend Generation Test (optional, costs ~$0.20)
TEST 3: UI Manual Test (see checklist above)

""")

    # TEST 1: Imports
    if not test_imports():
        print("\n❌ Import test failed. Fix imports before proceeding.")
        return 1

    # TEST 2: Backend (optional)
    print("\n" + "=" * 80)
    print("Optional: Run backend test?")
    print("=" * 80)
    print("\nThis will actually generate a MasterPlan and test the backend logic.")
    print("Cost: ~$0.20 in Anthropic API calls")
    print()

    response = input("Run backend test? (y/N): ")
    if response.lower() == 'y':
        if not asyncio.run(test_masterplan_generation_programmatic()):
            print("\n❌ Backend test failed.")
            return 1

    # TEST 3: UI Manual
    print("\n" + "=" * 80)
    print("UI Manual Test Instructions")
    print("=" * 80)
    print("""
To test the complete UI flow:

1. Start Backend:
   cd src/api
   uvicorn main:app --reload --port 8000

2. Start Frontend:
   cd src/ui
   npm run dev

3. Open Browser:
   http://localhost:5173

4. In Chat, type:
   /masterplan Build a simple Task Management API with CRUD operations

5. Watch for:
   ✓ Progress indicator appears
   ✓ Token counter updates every 5 seconds
   ✓ Phase text changes
   ✓ Entity counters update (Fases, Milestones, Tareas)
   ✓ Progress bar advances
   ✓ Timeline items change status
   ✓ Completion message with confetti 🎉
   ✓ Progress indicator disappears after 3 seconds

Expected duration: 90-120 seconds
Expected cost: $0.18

""")

    print("\n" + "=" * 80)
    print("✅ All automated tests passed!")
    print("   Follow manual test instructions above to verify UI")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
