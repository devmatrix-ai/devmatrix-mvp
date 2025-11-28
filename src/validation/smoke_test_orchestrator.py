"""
Smoke Test Orchestrator

Phase 6 of Bug #107: LLM-Driven Smoke Test Generation

Coordinates all smoke test agents through the complete workflow:
1. Planner → Generate test plan from IR
2. Seed Data → Generate seed_db.py from plan
3. Executor → Run HTTP scenarios
4. Validator → Analyze results
"""
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Optional
import structlog

from src.cognitive.ir.application_ir import ApplicationIR
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
from src.validation.smoke_test_models import SmokeTestPlan, SmokeTestReport
from src.validation.agents.planner_agent import SmokeTestPlannerAgent
from src.validation.agents.seed_data_agent import SeedDataAgent
from src.validation.agents.executor_agent import ScenarioExecutorAgent
from src.validation.agents.validation_agent import ValidationAgent

logger = structlog.get_logger(__name__)


class SmokeTestOrchestrator:
    """
    Coordinates all smoke test agents through the complete workflow.

    Usage:
        orchestrator = SmokeTestOrchestrator(llm_client)
        report = await orchestrator.run_smoke_tests(
            spec_path=Path("spec.md"),
            ir=application_ir,
            app_dir=Path("generated_app/")
        )
    """

    def __init__(self, llm_client: Optional[EnhancedAnthropicClient] = None):
        self.llm = llm_client or EnhancedAnthropicClient()

        # Initialize agents
        self.planner = SmokeTestPlannerAgent(self.llm)
        self.seed_generator = SeedDataAgent(self.llm)
        self.validator = ValidationAgent(self.llm)

    async def run_smoke_tests(
        self,
        spec_path: Path,
        ir: ApplicationIR,
        app_dir: Path,
        base_url: str = "http://localhost:8000",
        skip_server_start: bool = False
    ) -> SmokeTestReport:
        """
        Complete smoke test workflow using specialized agents.

        Args:
            spec_path: Path to API specification
            ir: Application Intermediate Representation
            app_dir: Directory with generated application
            base_url: Server URL to test against
            skip_server_start: If True, assume server is already running

        Returns:
            SmokeTestReport with results and analysis
        """
        logger.info("🚀 Smoke Test Orchestrator: Starting full workflow")
        start_time = time.time()

        try:
            # Phase 1: Generate test plan
            logger.info("━━━ Phase 1: Generate Test Plan ━━━")
            spec_content = spec_path.read_text() if spec_path.exists() else ""
            plan = await self.planner.generate_plan(ir, spec_content)

            # Save plan for debugging
            plan_path = app_dir / "smoke_test_plan.json"
            plan_path.write_text(plan.to_json())
            logger.info(f"   Saved plan to {plan_path}")

            # Phase 2: Generate seed data
            logger.info("━━━ Phase 2: Generate Seed Data ━━━")
            seed_script = self.seed_generator.generate_seed_script(plan, ir)

            scripts_dir = app_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            seed_path = scripts_dir / "seed_db.py"
            seed_path.write_text(seed_script)
            logger.info(f"   Saved seed script to {seed_path}")

            # Phase 3: Start server (if needed)
            server_process = None
            if not skip_server_start:
                logger.info("━━━ Phase 3: Start Server ━━━")
                server_process = await self._start_server(app_dir)
                await self._wait_for_server(base_url)

            try:
                # Run seed script
                logger.info("━━━ Phase 3b: Seed Database ━━━")
                await self._run_seed_script(app_dir)

                # Phase 4: Execute scenarios
                logger.info("━━━ Phase 4: Execute Scenarios ━━━")
                executor = ScenarioExecutorAgent(base_url)
                results = await executor.execute_all(plan)

                # Phase 5: Analyze results
                logger.info("━━━ Phase 5: Analyze Results ━━━")
                report = await self.validator.analyze_results(results, plan)

            finally:
                # Cleanup: Stop server
                if server_process:
                    logger.info("━━━ Cleanup: Stop Server ━━━")
                    await self._stop_server(server_process)

            # Log summary
            elapsed = time.time() - start_time
            logger.info(f"━━━ Smoke Test Complete in {elapsed:.1f}s ━━━")
            logger.info(f"   Status: {report.status}")
            logger.info(f"   Passed: {report.metrics.passed}/{report.metrics.total}")

            return report

        except Exception as e:
            logger.error(f"❌ Smoke test workflow failed: {e}")
            raise

    async def run_with_existing_plan(
        self,
        plan: SmokeTestPlan,
        app_dir: Path,
        base_url: str = "http://localhost:8000",
        skip_server_start: bool = False
    ) -> SmokeTestReport:
        """
        Run smoke tests with an existing plan (skip planning phase).

        Useful for re-running tests without regenerating the plan.
        """
        logger.info("🔄 Running smoke tests with existing plan")

        server_process = None
        if not skip_server_start:
            server_process = await self._start_server(app_dir)
            await self._wait_for_server(base_url)

        try:
            # Execute scenarios
            executor = ScenarioExecutorAgent(base_url)
            results = await executor.execute_all(plan)

            # Analyze results
            report = await self.validator.analyze_results(results, plan)

            return report

        finally:
            if server_process:
                await self._stop_server(server_process)

    async def _start_server(self, app_dir: Path) -> subprocess.Popen:
        """Start the generated application server."""
        logger.info("   Starting server...")

        # Use Docker Compose if available
        compose_file = app_dir / "docker-compose.yml"
        if compose_file.exists():
            process = subprocess.Popen(
                ["docker-compose", "up", "-d"],
                cwd=app_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return process

        # Fallback: Start with uvicorn
        process = subprocess.Popen(
            ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return process

    async def _wait_for_server(
        self,
        base_url: str,
        timeout: float = 60.0,
        interval: float = 1.0
    ):
        """Wait for server to become ready."""
        import httpx

        logger.info(f"   Waiting for server at {base_url}...")
        start = time.time()

        health_url = f"{base_url}/health"

        async with httpx.AsyncClient() as client:
            while time.time() - start < timeout:
                try:
                    response = await client.get(health_url, timeout=5.0)
                    if response.status_code == 200:
                        logger.info("   ✅ Server is ready")
                        return
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass

                await asyncio.sleep(interval)

        raise TimeoutError(f"Server did not become ready within {timeout}s")

    async def _run_seed_script(self, app_dir: Path):
        """Run the seed_db.py script."""
        seed_path = app_dir / "scripts" / "seed_db.py"
        if not seed_path.exists():
            logger.warning("   ⚠️ No seed script found, skipping")
            return

        logger.info("   Running seed script...")

        process = await asyncio.create_subprocess_exec(
            "python", str(seed_path),
            cwd=app_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"   ❌ Seed script failed: {stderr.decode()}")
            raise RuntimeError(f"Seed script failed: {stderr.decode()}")

        logger.info("   ✅ Seed data created")

    async def _stop_server(self, process: subprocess.Popen):
        """Stop the server process."""
        logger.info("   Stopping server...")

        # Try Docker Compose down first
        try:
            subprocess.run(
                ["docker-compose", "down"],
                capture_output=True,
                timeout=30
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Kill the process
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

        logger.info("   ✅ Server stopped")
