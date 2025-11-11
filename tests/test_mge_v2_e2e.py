#!/usr/bin/env python3
"""
E2E Test for MGE V2 MasterPlan Generation
Tests: Auth → WebSocket Connect → Message → MasterPlan Generation → Validation
"""

import asyncio
import json
import sys
import time
from typing import Optional
import socketio
import requests
import psycopg2

# Configuration
API_URL = "http://localhost:8000"
WS_URL = "http://localhost:8000"
TEST_EMAIL = "test@devmatrix.com"
TEST_PASSWORD = "Test123!"
PROMPT = "Create a REST API for a todo list application with user authentication"

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "devmatrix",
    "password": "devmatrix",
    "database": "devmatrix"
}

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'


class MGEv2Test:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.conversation_id = None
        self.message_id = None
        self.masterplan_id = None
        # Create AsyncClient with explicit EIO version and logging
        self.sio = socketio.AsyncClient(
            logger=True,
            engineio_logger=True,
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=1
        )
        self.generation_started = False
        self.generation_completed = False
        self.progress_updates = []

    def log(self, message: str, color: str = NC):
        print(f"{color}{message}{NC}")

    def get_db_connection(self):
        return psycopg2.connect(**DB_CONFIG)

    async def step1_auth(self):
        """Step 1: Authentication"""
        self.log(f"\n{BLUE}[1/6]{NC} Authenticating...")

        response = requests.post(
            f"{API_URL}/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )

        if response.status_code != 200:
            self.log(f"✗ Authentication failed: {response.text}", RED)
            return False

        data = response.json()
        self.token = data["access_token"]
        self.user_id = data["user"]["user_id"]

        self.log(f"{GREEN}✓ Authenticated{NC}")
        self.log(f"{GREEN}✓ User ID: {self.user_id}{NC}")
        return True

    async def step2_create_conversation(self):
        """Step 2: Create conversation"""
        self.log(f"\n{BLUE}[2/6]{NC} Creating conversation...")

        conn = self.get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO conversations (conversation_id, user_id, title, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, 'E2E Test', NOW(), NOW())
            RETURNING conversation_id
        """, (self.user_id,))

        self.conversation_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close()
        conn.close()

        self.log(f"{GREEN}✓ Conversation: {self.conversation_id}{NC}")
        return True

    async def step3_setup_websocket(self):
        """Step 3: Setup WebSocket connection"""
        self.log(f"\n{BLUE}[3/6]{NC} Connecting to WebSocket...")

        # Setup event handlers
        @self.sio.on('connect')
        async def on_connect():
            self.log(f"{GREEN}✓ WebSocket connected{NC}")

        @self.sio.on('message')
        async def on_message(data):
            msg_type = data.get('type', '')

            if msg_type == 'masterplan.generation_started':
                self.generation_started = True
                self.masterplan_id = data.get('masterplan_id')
                self.log(f"\n{GREEN}✓ MasterPlan generation started: {self.masterplan_id}{NC}")

            elif msg_type == 'masterplan.phase_completed':
                phase_name = data.get('phase_name', 'Unknown')
                self.log(f"{YELLOW}  Phase completed: {phase_name}{NC}")

            elif msg_type == 'masterplan.generation_completed':
                self.generation_completed = True
                self.log(f"\n{GREEN}✓ MasterPlan generation completed{NC}")

            elif msg_type == 'masterplan.generation_failed':
                error = data.get('error', 'Unknown error')
                self.log(f"\n{RED}✗ MasterPlan generation failed: {error}{NC}", RED)

            elif msg_type == 'progress':
                progress = data.get('progress', {})
                self.progress_updates.append(progress)

            # Detect completion via 'message' type with 'done: true'
            elif msg_type == 'message':
                # Check if this is the completion message
                if data.get('done') is True:
                    metadata = data.get('metadata', {})
                    if metadata.get('type') == 'complete':
                        self.generation_completed = True
                        self.masterplan_id = metadata.get('masterplan_id', self.masterplan_id)
                        self.log(f"\n{GREEN}✓ MasterPlan generation completed{NC}")

        @self.sio.on('error')
        async def on_error(data):
            self.log(f"{RED}✗ WebSocket error: {data}{NC}", RED)

        # Connect without auth (auth is done in join_chat event)
        await self.sio.connect(
            WS_URL,
            socketio_path='/socket.io',
            wait_timeout=10
        )

        # Join chat room with authentication token
        await self.sio.emit('join_chat', {
            'conversation_id': self.conversation_id,
            'token': self.token
        })

        await asyncio.sleep(1)  # Give time for connection to stabilize
        return True

    async def step4_send_message(self):
        """Step 4: Send message via WebSocket"""
        self.log(f"\n{BLUE}[4/6]{NC} Sending message...")
        self.log(f"Prompt: {PROMPT}")

        # Send message via WebSocket
        await self.sio.emit('send_message', {
            'conversation_id': self.conversation_id,
            'content': PROMPT
        })

        self.log(f"{GREEN}✓ Message sent{NC}")
        return True

    async def step5_monitor_generation(self):
        """Step 5: Monitor MasterPlan generation"""
        self.log(f"\n{BLUE}[5/6]{NC} Monitoring generation...")

        max_wait = 600  # 10 minutes (for full code generation + atomization)
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if self.generation_completed:
                break

            if self.generation_started and not self.masterplan_id:
                # Try to get masterplan_id from database
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT masterplan_id, status, total_phases
                    FROM masterplans
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (self.user_id,))

                result = cur.fetchone()
                if result:
                    self.masterplan_id = str(result[0])
                    status = result[1]
                    phases = result[2] or 0

                    print(f"\r{YELLOW}Status: {status} | Phases: {phases}{NC}    ", end='', flush=True)

                cur.close()
                conn.close()

            await asyncio.sleep(3)

        elapsed = time.time() - start_time

        if not self.generation_completed:
            self.log(f"\n{RED}✗ Timeout: Generation did not complete after {elapsed:.0f}s{NC}", RED)
            return False

        self.log(f"\n{GREEN}✓ Generation completed in {elapsed:.0f}s{NC}")
        return True

    async def step6_validate(self):
        """Step 6: Validate generated artifacts"""
        self.log(f"\n{BLUE}[6/6]{NC} Validating artifacts...")

        if not self.masterplan_id:
            self.log(f"{RED}✗ No MasterPlan ID{NC}", RED)
            return False

        conn = self.get_db_connection()
        cur = conn.cursor()

        # Get masterplan details
        cur.execute("""
            SELECT project_name, status, total_phases, total_tasks, total_subtasks
            FROM masterplans
            WHERE masterplan_id = %s
        """, (self.masterplan_id,))

        result = cur.fetchone()
        if not result:
            self.log(f"{RED}✗ MasterPlan not found in database{NC}", RED)
            return False

        project_name, status, total_phases, total_tasks, total_subtasks = result

        # Get atom count (MGE V2 uses atoms instead of subtasks)
        cur.execute("""
            SELECT COUNT(*) as atom_count
            FROM atomic_units
            WHERE masterplan_id = %s
        """, (self.masterplan_id,))

        atom_result = cur.fetchone()
        total_atoms = atom_result[0] if atom_result else 0

        self.log("\n===================================")
        self.log("Final Results")
        self.log("===================================")
        self.log(f"{BLUE}Project:{NC} {project_name}")
        self.log(f"{BLUE}MasterPlan ID:{NC} {self.masterplan_id}")
        self.log(f"{BLUE}Status:{NC} {status}")
        self.log(f"{BLUE}Phases:{NC} {total_phases or 0}")
        self.log(f"{BLUE}Tasks:{NC} {total_tasks or 0}")
        self.log(f"{BLUE}Atoms:{NC} {total_atoms or 0}")
        self.log("")

        # Validate
        tests_passed = 0
        tests_failed = 0

        # Status check - accept both 'completed' and 'COMPLETED'
        if status and status.upper() == 'COMPLETED':
            self.log(f"{GREEN}✓ Status is completed{NC}")
            tests_passed += 1
        else:
            self.log(f"{RED}✗ Status is not completed: {status}{NC}", RED)
            tests_failed += 1

        if total_phases and total_phases > 0:
            self.log(f"{GREEN}✓ Has phases ({total_phases}){NC}")
            tests_passed += 1
        else:
            self.log(f"{RED}✗ No phases generated{NC}", RED)
            tests_failed += 1

        if total_tasks and total_tasks > 0:
            self.log(f"{GREEN}✓ Has tasks ({total_tasks}){NC}")
            tests_passed += 1
        else:
            self.log(f"{RED}✗ No tasks generated{NC}", RED)
            tests_failed += 1

        # MGE V2 uses atoms instead of subtasks
        if total_atoms and total_atoms > 0:
            self.log(f"{GREEN}✓ Has atoms ({total_atoms}){NC}")
            tests_passed += 1
        else:
            self.log(f"{RED}✗ No atoms generated{NC}", RED)
            tests_failed += 1

        cur.close()
        conn.close()

        self.log("")
        self.log("===================================")
        if tests_failed == 0:
            self.log(f"{GREEN}✓ All tests passed ({tests_passed}/4){NC}")
            return True
        else:
            self.log(f"{RED}✗ Some tests failed ({tests_passed} passed, {tests_failed} failed){NC}", RED)
            return False

    async def cleanup(self):
        """Cleanup resources"""
        if self.sio.connected:
            await self.sio.disconnect()

    async def run(self):
        """Run the complete E2E test"""
        self.log("==========================================")
        self.log("MGE V2 E2E Test")
        self.log("==========================================")

        try:
            if not await self.step1_auth():
                return 1

            if not await self.step2_create_conversation():
                return 1

            if not await self.step3_setup_websocket():
                return 1

            if not await self.step4_send_message():
                return 1

            if not await self.step5_monitor_generation():
                return 1

            if not await self.step6_validate():
                return 1

            return 0

        except Exception as e:
            self.log(f"\n{RED}✗ Test failed with exception: {e}{NC}", RED)
            import traceback
            traceback.print_exc()
            return 1

        finally:
            await self.cleanup()


async def main():
    test = MGEv2Test()
    exit_code = await test.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
