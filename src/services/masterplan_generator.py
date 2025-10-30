"""
MasterPlan Generator - Monolithic Approach

Generates complete MasterPlan (120 tasks) from Discovery Document in a single LLM call.

Flow:
1. Load DiscoveryDocument from database
2. Retrieve similar examples from RAG (if available)
3. Generate complete MasterPlan with LLM (Sonnet 4.5)
4. Parse and validate MasterPlan structure
5. Save to database (MasterPlan, Phases, Milestones, Tasks)
6. Return masterplan_id

Output: ~17K tokens (fits in Sonnet's 64K output limit)
Cost: ~$0.32 per MasterPlan (with prompt caching)
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.llm import EnhancedAnthropicClient, TaskType, TaskComplexity
from src.models.masterplan import (
    DiscoveryDocument,
    MasterPlan,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    MasterPlanSubtask,
    MasterPlanStatus,
    TaskStatus,
    TaskComplexity as DBTaskComplexity,
    PhaseType
)
from src.config.database import get_db_context
from src.rag import create_retriever, create_vector_store, create_embedding_model
from src.observability import get_logger
from src.observability.metrics_collector import MetricsCollector
from src.websocket import WebSocketManager

logger = get_logger("masterplan_generator")


# MasterPlan Generation System Prompt
MASTERPLAN_SYSTEM_PROMPT = """You are an expert software architect and project planner.

Your task is to generate a complete, executable MasterPlan for implementing a software project based on DDD discovery.

## MasterPlan Structure:

The MasterPlan consists of **3 Phases** with **120 ULTRA-ATOMIC tasks** (complete production-ready implementation):

### Phase 1: Setup (35-40 tasks)
- Infrastructure setup (database, Redis, Docker) - Critical config files only
- Project structure & core configuration
- Essential models and schemas - Group related models
- Basic API foundation
- Authentication/authorization - Core implementation

### Phase 2: Core (50-60 tasks)
- Implement key aggregates and entities - Focus on main business logic
- Core business logic and domain services
- Essential CRUD operations
- Critical features and workflows
- Key integrations between bounded contexts
- Main API endpoints

### Phase 3: Polish (20-30 tasks)
- Testing (focus on critical paths)
- Error handling and validation
- Performance optimization (key areas)
- Essential documentation
- Deployment preparation

## ULTRA-ATOMIC Task Philosophy:

**Each task MUST be:**
1. **Single Responsibility**: Exactly ONE file creation/modification OR ONE logical operation
2. **Autonomous**: No human input needed during execution
3. **Verifiable**: Has clear success criteria
4. **Small**: 200-800 tokens of code output (NOT 500-5000!)
5. **Independent**: Minimal dependencies on other tasks

## Task Structure with SUBTASKS:

Each task must include:
- **task_number**: Global task number (1-150)
- **name**: Ultra-specific task name (max 300 chars) - e.g., "Create User SQLAlchemy model"
- **description**: Precise description focusing on WHAT file and WHAT changes
- **complexity**: low, medium, high, critical
- **depends_on_tasks**: List of task_numbers this depends on (empty array if none)
- **target_files**: EXACTLY the files to create/modify (usually 1 file per task!)
- **estimated_tokens**: 200-800 (ultra-atomic means small!)
- **subtasks**: Array of 3-7 micro-steps for autonomous execution

### Subtask Structure:

Each subtask is a SPECIFIC action:
- **subtask_number**: 1, 2, 3, etc.
- **name**: Micro-action description (e.g., "Import SQLAlchemy dependencies")
- **description**: Exact code block or operation to perform

**Subtask Examples for "Create User SQLAlchemy model":**
1. "Import SQLAlchemy Base, Column, String, DateTime, UUID"
2. "Define User class inheriting from Base"
3. "Add __tablename__ = 'users'"
4. "Add id field as UUID primary key"
5. "Add email field as unique String(255)"
6. "Add password_hash field as String(255)"
7. "Add created_at and updated_at timestamp fields"

## Output Format (JSON):

```json
{
  "project_name": "Project Name",
  "description": "Brief project description",
  "tech_stack": {
    "backend": "Python + FastAPI",
    "frontend": "React + TypeScript",
    "database": "PostgreSQL",
    "cache": "Redis",
    "other": ["Docker", "Alembic", etc.]
  },
  "architecture_style": "monolithic|microservices|serverless",
  "phases": [
    {
      "phase_number": 1,
      "name": "Setup",
      "description": "Infrastructure and foundation",
      "milestones": [
        {
          "milestone_number": 1,
          "name": "Database Setup",
          "description": "PostgreSQL schema and models",
          "depends_on_milestones": [],
          "tasks": [
            {
              "task_number": 1,
              "name": "Create User SQLAlchemy model",
              "description": "Implement User SQLAlchemy model in src/models/user.py with id, email, password_hash, created_at fields",
              "complexity": "low",
              "depends_on_tasks": [],
              "target_files": ["src/models/user.py"],
              "estimated_tokens": 600,
              "subtasks": [
                {
                  "subtask_number": 1,
                  "name": "Import SQLAlchemy dependencies",
                  "description": "from sqlalchemy import Column, String, DateTime, UUID; from src.database import Base"
                },
                {
                  "subtask_number": 2,
                  "name": "Define User class",
                  "description": "class User(Base): with __tablename__ = 'users'"
                },
                {
                  "subtask_number": 3,
                  "name": "Add id field",
                  "description": "id = Column(UUID, primary_key=True, default=uuid.uuid4)"
                },
                {
                  "subtask_number": 4,
                  "name": "Add email field",
                  "description": "email = Column(String(255), unique=True, nullable=False)"
                },
                {
                  "subtask_number": 5,
                  "name": "Add password_hash field",
                  "description": "password_hash = Column(String(255), nullable=False)"
                },
                {
                  "subtask_number": 6,
                  "name": "Add timestamp fields",
                  "description": "created_at = Column(DateTime, default=datetime.utcnow); updated_at = Column(DateTime, onupdate=datetime.utcnow)"
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "total_tasks": 120,
  "estimated_cost_usd": 15.80,
  "estimated_duration_minutes": 45
}
```

## Guidelines:

1. **ULTRA-ATOMIC Principle**: Each task = ONE file operation OR ONE specific function. Break everything down to the smallest possible autonomous unit.
2. **Subtasks are MANDATORY**: Every task MUST have 3-7 subtasks describing the exact micro-steps for autonomous execution.
3. **Dependency Management**: Tasks must respect dependencies. A task can only depend on tasks with lower task_numbers.
4. **Granularity**: Each task should generate 200-800 tokens (ultra-small!). If bigger, split into multiple tasks.
5. **Complexity Distribution**:
   - Low: 50% of tasks (one model, one endpoint, one config file, one util function)
   - Medium: 35% of tasks (business logic methods, validation layers, service classes)
   - High: 12% of tasks (complex integrations, authentication flow, real-time features)
   - Critical: 3% of tasks (payment processing, data migrations, security middleware)
6. **File Paths**: Use standard project structure (src/models, src/api, src/services, src/utils, tests/, etc.)
7. **Progressive Complexity**: Start simple (Phase 1), build up to complex (Phase 2), finish with polish (Phase 3)
8. **Realistic Estimates**: Token estimates 200-800 per task (ultra-atomic means small!)
9. **Subtask Detail Level**: Each subtask should be specific enough that an LLM can execute it line-by-line without ambiguity.

**IMPORTANT**:
- Return ONLY valid JSON, no markdown, no explanations outside the JSON
- Generate EXACTLY 120 tasks total (complete production-ready implementation)
- Cover ALL aspects: Auth, RBAC, Users, Organizations, Projects, Boards, Issues, Sprints, Comments, Attachments, Notifications, Search, Reporting, Real-time, API/Webhooks
- All task_numbers must be sequential starting from 1
- Dependencies must reference valid task_numbers
- EVERY task MUST include a "subtasks" array with 3-5 items (concise)
- Keep descriptions concise to reduce token count
"""


class MasterPlanGenerator:
    """
    MasterPlan Generator for creating complete 120-task production-ready plans.

    Usage:
        generator = MasterPlanGenerator()
        masterplan_id = await generator.generate_masterplan(
            discovery_id=UUID("..."),
            session_id="session_123",
            user_id="user_456"
        )
    """

    def __init__(
        self,
        llm_client: Optional[EnhancedAnthropicClient] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        use_rag: bool = True,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize MasterPlan Generator.

        Args:
            llm_client: LLM client (creates new if not provided)
            metrics_collector: Metrics collector
            use_rag: Whether to use RAG for example retrieval
            websocket_manager: WebSocket manager for real-time progress updates (optional)
        """
        self.llm = llm_client or EnhancedAnthropicClient()
        self.metrics = metrics_collector or MetricsCollector()
        self.use_rag = use_rag
        self.ws_manager = websocket_manager

        # Initialize RAG components if enabled
        if self.use_rag:
            try:
                embedding_model = create_embedding_model()
                vector_store = create_vector_store(embedding_model)
                self.retriever = create_retriever(vector_store)
                logger.info("RAG retriever initialized for MasterPlan generation")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG: {e}. Continuing without RAG.")
                self.use_rag = False
                self.retriever = None
        else:
            self.retriever = None

        logger.info("MasterPlanGenerator initialized", use_rag=self.use_rag, has_websocket=bool(websocket_manager))

    async def generate_masterplan(
        self,
        discovery_id: UUID,
        session_id: str,
        user_id: str
    ) -> UUID:
        """
        Generate complete MasterPlan from Discovery with real-time progress updates.

        Args:
            discovery_id: UUID of DiscoveryDocument
            session_id: Session identifier
            user_id: User identifier

        Returns:
            masterplan_id: UUID of created MasterPlan

        Raises:
            ValueError: If discovery not found or invalid
            RuntimeError: If generation fails
        """
        import time
        overall_start_time = time.time()

        logger.info(
            "Starting MasterPlan generation",
            discovery_id=str(discovery_id),
            session_id=session_id,
            user_id=user_id
        )

        # Record start metric
        self.metrics.increment_counter(
            "masterplan_requests_total",
            labels={"session_id": session_id},
            help_text="Total MasterPlan generation requests"
        )

        try:
            # Load discovery
            discovery = self._load_discovery(discovery_id)

            if not discovery:
                raise ValueError(f"Discovery not found: {discovery_id}")

            # Emit generation start event
            if self.ws_manager:
                logger.info("🚀 Emitting masterplan_generation_start WebSocket event", session_id=session_id)
                await self.ws_manager.emit_masterplan_generation_start(
                    session_id=session_id,
                    discovery_id=str(discovery_id),
                    estimated_tokens=17000,
                    estimated_duration_seconds=90
                )
            else:
                logger.warning("⚠️  WebSocket manager not available, skipping progress events")

            # Retrieve similar examples from RAG
            rag_examples = await self._retrieve_rag_examples(discovery)

            # Generate MasterPlan with LLM (with progress updates)
            masterplan_json = await self._generate_masterplan_llm_with_progress(
                discovery=discovery,
                rag_examples=rag_examples,
                session_id=session_id
            )

            # Parse MasterPlan
            masterplan_data = self._parse_masterplan(masterplan_json)

            # Emit parsing complete event
            if self.ws_manager:
                phases = masterplan_data.get("phases", [])
                total_milestones = sum(len(p.get("milestones", [])) for p in phases)
                total_tasks = masterplan_data.get("total_tasks", 120)

                await self.ws_manager.emit_masterplan_parsing_complete(
                    session_id=session_id,
                    total_phases=len(phases),
                    total_milestones=total_milestones,
                    total_tasks=total_tasks
                )

            # Validate MasterPlan
            if self.ws_manager:
                await self.ws_manager.emit_masterplan_validation_start(session_id)

            self._validate_masterplan(masterplan_data)

            # Save to database
            if self.ws_manager:
                phases = masterplan_data.get("phases", [])
                total_milestones = sum(len(p.get("milestones", [])) for p in phases)
                total_tasks = masterplan_data.get("total_tasks", 120)
                total_entities = len(phases) + total_milestones + total_tasks

                await self.ws_manager.emit_masterplan_saving_start(
                    session_id=session_id,
                    total_entities=total_entities
                )

            masterplan_id = self._save_masterplan(
                discovery_id=discovery_id,
                session_id=session_id,
                user_id=user_id,
                masterplan_data=masterplan_data,
                llm_model=masterplan_json.get("model"),
                llm_cost=masterplan_json.get("cost_usd")
            )

            # Calculate total duration
            total_duration = time.time() - overall_start_time

            # Emit generation complete event
            if self.ws_manager:
                phases = masterplan_data.get("phases", [])
                total_milestones = sum(len(p.get("milestones", [])) for p in phases)

                await self.ws_manager.emit_masterplan_generation_complete(
                    session_id=session_id,
                    masterplan_id=str(masterplan_id),
                    project_name=masterplan_data.get("project_name", "Unknown"),
                    total_phases=len(phases),
                    total_milestones=total_milestones,
                    total_tasks=masterplan_data.get("total_tasks", 50),
                    generation_cost_usd=masterplan_json.get("cost_usd", 0),
                    duration_seconds=total_duration,
                    estimated_total_cost_usd=masterplan_data.get("estimated_cost", 0),
                    estimated_duration_minutes=masterplan_data.get("estimated_duration", 0)
                )

            # Record success
            self.metrics.increment_counter(
                "masterplan_success_total",
                labels={"session_id": session_id},
                help_text="Successful MasterPlan generations"
            )

            logger.info(
                "MasterPlan generation completed successfully",
                masterplan_id=str(masterplan_id),
                discovery_id=str(discovery_id),
                total_tasks=masterplan_data.get("total_tasks"),
                phases_count=len(masterplan_data.get("phases", [])),
                duration_seconds=total_duration
            )

            return masterplan_id

        except Exception as e:
            # Record failure
            self.metrics.increment_counter(
                "masterplan_failures_total",
                labels={"session_id": session_id, "error_type": type(e).__name__},
                help_text="Failed MasterPlan generations"
            )

            logger.error(
                "MasterPlan generation failed",
                discovery_id=str(discovery_id),
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise RuntimeError(f"MasterPlan generation failed: {str(e)}") from e

    def _load_discovery(self, discovery_id: UUID) -> Optional[DiscoveryDocument]:
        """Load DiscoveryDocument from database."""
        with get_db_context() as db:
            discovery = db.query(DiscoveryDocument).filter(
                DiscoveryDocument.discovery_id == discovery_id
            ).first()

            return discovery

    async def _retrieve_rag_examples(self, discovery: DiscoveryDocument) -> List[Dict]:
        """
        Retrieve similar examples from RAG.

        Args:
            discovery: DiscoveryDocument

        Returns:
            List of similar code examples
        """
        if not self.use_rag or not self.retriever:
            return []

        try:
            # Build query from discovery
            query = f"Domain: {discovery.domain}. Bounded contexts: {', '.join([bc['name'] for bc in discovery.bounded_contexts])}"

            # Retrieve top 5 similar examples
            results = self.retriever.retrieve(
                query=query,
                top_k=5,
                min_similarity=0.7
            )

            logger.info(f"Retrieved {len(results)} RAG examples for MasterPlan generation")

            return [
                {
                    "code": r.code,
                    "metadata": r.metadata,
                    "similarity": r.similarity
                }
                for r in results
            ]

        except Exception as e:
            logger.warning(f"Failed to retrieve RAG examples: {e}. Continuing without RAG.")
            return []

    async def _generate_masterplan_llm_with_progress(
        self,
        discovery: DiscoveryDocument,
        rag_examples: List[Dict],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate MasterPlan with simulated progress updates.

        Args:
            discovery: DiscoveryDocument
            rag_examples: Similar examples from RAG
            session_id: Session ID for WebSocket events

        Returns:
            Dict with MasterPlan JSON and metadata
        """
        import time

        # Start generation in background
        generation_task = asyncio.create_task(
            self._generate_masterplan_llm(discovery, rag_examples)
        )

        # Simulate progress updates while waiting
        estimated_total_tokens = 17000
        estimated_duration = 90  # seconds
        start_time = time.time()
        last_progress_time = start_time

        # Progress simulation intervals (every 5 seconds)
        progress_interval = 5

        # Phase descriptions for progress
        phases = [
            "Analizando Discovery Document...",
            "Generando estructura del plan...",
            "Creando fases del proyecto...",
            "Generando milestones...",
            "Creando tareas (1-15)...",
            "Creando tareas (16-30)...",
            "Creando tareas (31-45)...",
            "Creando tareas (46-50)...",
            "Finalizando estructura...",
            "Optimizando dependencias...",
        ]

        phase_index = 0

        while not generation_task.done():
            await asyncio.sleep(1)  # Check every second

            current_time = time.time()
            elapsed = current_time - start_time

            # Emit progress every 5 seconds
            if current_time - last_progress_time >= progress_interval and self.ws_manager:
                # Conservative progress estimation (cap at 90% until done)
                progress_ratio = min(elapsed / estimated_duration, 0.90)
                tokens_received = int(estimated_total_tokens * progress_ratio)

                # Get current phase
                current_phase = phases[min(phase_index, len(phases) - 1)]
                phase_index += 1

                await self.ws_manager.emit_masterplan_tokens_progress(
                    session_id=session_id,
                    tokens_received=tokens_received,
                    estimated_total=estimated_total_tokens,
                    current_phase=current_phase
                )

                last_progress_time = current_time

        # Get result
        result = await generation_task
        return result

    async def _generate_masterplan_llm(
        self,
        discovery: DiscoveryDocument,
        rag_examples: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate MasterPlan using LLM.

        Args:
            discovery: DiscoveryDocument
            rag_examples: Similar examples from RAG

        Returns:
            Dict with MasterPlan JSON and metadata
        """
        import time
        from uuid import UUID

        start_time = time.time()

        # Helper to convert non-serializable types
        def json_serializable(obj):
            if isinstance(obj, UUID):
                return str(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        # Build discovery context
        discovery_context = {
            "domain": discovery.domain,
            "user_request": discovery.user_request,
            "bounded_contexts": discovery.bounded_contexts,
            "aggregates": discovery.aggregates,
            "value_objects": discovery.value_objects,
            "domain_events": discovery.domain_events,
            "services": discovery.services
        }

        # Build RAG context
        rag_context = {
            "examples_count": len(rag_examples),
            "examples": rag_examples[:3]  # Limit to top 3 for token efficiency
        } if rag_examples else None

        # Build variable prompt
        variable_prompt = f"""Generate a complete MasterPlan (120 tasks) for the following project:

## Discovery Summary:
**Domain**: {discovery.domain}
**Bounded Contexts**: {len(discovery.bounded_contexts)} contexts
**Aggregates**: {len(discovery.aggregates)} aggregates
**Domain Events**: {len(discovery.domain_events)} events

## User Request:
{discovery.user_request}

## Full Discovery Details:
{json.dumps(discovery_context, indent=2, default=json_serializable)}

Generate a complete, executable MasterPlan with exactly 120 tasks organized in 3 phases covering ALL features needed for a production SaaS.
"""

        # Generate with caching
        # Using reduced max_tokens to avoid truncation (Anthropic limit ~20K actual output)
        # Streaming is automatically enabled for masterplan_generation in enhanced_anthropic_client
        response = await self.llm.generate_with_caching(
            task_type="masterplan_generation",  # Triggers automatic streaming
            complexity=TaskComplexity.HIGH,
            cacheable_context={
                "system_prompt": MASTERPLAN_SYSTEM_PROMPT,
                "discovery_doc": discovery_context,
                "rag_examples": rag_context
            },
            variable_prompt=variable_prompt,
            max_tokens=64000,  # Maximum for 120 tasks (Sonnet 4.5 supports up to 64K)
            temperature=0.7
        )

        duration = time.time() - start_time

        logger.info(
            "MasterPlan LLM generation complete",
            model=response["model"],
            cost_usd=response["cost_usd"],
            duration_seconds=duration,
            input_tokens=response["usage"]["input_tokens"],
            output_tokens=response["usage"]["output_tokens"],
            cached_tokens=response["usage"].get("cache_read_input_tokens", 0)
        )

        return {
            "content": response["content"],
            "model": response["model"],
            "cost_usd": response["cost_usd"],
            "usage": response["usage"],
            "duration_seconds": duration
        }

    def _parse_masterplan(self, masterplan_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate MasterPlan JSON.

        Args:
            masterplan_response: Response from LLM

        Returns:
            Parsed MasterPlan data

        Raises:
            ValueError: If JSON is invalid
        """
        content = masterplan_response["content"]

        # Extract JSON from markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Parse JSON
        try:
            masterplan_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse MasterPlan JSON", error=str(e), content=content[:1000])
            raise ValueError(f"Invalid JSON from LLM: {str(e)}") from e

        logger.debug(
            "MasterPlan parsed successfully",
            project_name=masterplan_data.get("project_name"),
            total_tasks=masterplan_data.get("total_tasks"),
            phases=len(masterplan_data.get("phases", []))
        )

        return masterplan_data

    def _validate_masterplan(self, masterplan_data: Dict[str, Any]):
        """
        Validate MasterPlan structure.

        Args:
            masterplan_data: Parsed MasterPlan

        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        required_fields = ["project_name", "tech_stack", "phases", "total_tasks"]
        missing = [f for f in required_fields if f not in masterplan_data]
        if missing:
            raise ValueError(f"MasterPlan missing required fields: {missing}")

        # Check total tasks
        total_tasks = masterplan_data.get("total_tasks", 0)
        if total_tasks < 100 or total_tasks > 150:
            logger.warning(f"MasterPlan has {total_tasks} tasks (expected 100-150 for production SaaS)")

        # Check phases
        phases = masterplan_data.get("phases", [])
        if len(phases) != 3:
            raise ValueError(f"MasterPlan must have exactly 3 phases, got {len(phases)}")

        # Count actual tasks
        actual_task_count = sum(
            len(milestone.get("tasks", []))
            for phase in phases
            for milestone in phase.get("milestones", [])
        )

        if actual_task_count != total_tasks:
            logger.warning(
                f"Task count mismatch: declared={total_tasks}, actual={actual_task_count}"
            )

        logger.info(
            "MasterPlan validated",
            total_tasks=total_tasks,
            phases=len(phases),
            actual_tasks=actual_task_count
        )

    def _save_masterplan(
        self,
        discovery_id: UUID,
        session_id: str,
        user_id: str,
        masterplan_data: Dict[str, Any],
        llm_model: str,
        llm_cost: float
    ) -> UUID:
        """
        Save MasterPlan to database.

        Args:
            discovery_id: Discovery UUID
            session_id: Session ID
            user_id: User ID
            masterplan_data: Parsed MasterPlan data
            llm_model: Model used
            llm_cost: Cost in USD

        Returns:
            masterplan_id: UUID of saved MasterPlan
        """
        with get_db_context() as db:
            # Create MasterPlan
            masterplan = MasterPlan(
                discovery_id=discovery_id,
                session_id=session_id,
                user_id=user_id,
                project_name=masterplan_data["project_name"],
                description=masterplan_data.get("description"),
                status=MasterPlanStatus.DRAFT,
                tech_stack=masterplan_data["tech_stack"],
                architecture_style=masterplan_data.get("architecture_style"),
                total_tasks=masterplan_data["total_tasks"],
                llm_model=llm_model,
                generation_cost_usd=llm_cost,
                estimated_cost_usd=masterplan_data.get("estimated_cost_usd"),
                estimated_duration_minutes=masterplan_data.get("estimated_duration_minutes")
            )

            db.add(masterplan)
            db.flush()  # Get masterplan_id without committing

            # Create Phases, Milestones, Tasks
            task_number_to_uuid = {}  # Map task_number → task_id UUID

            for phase_data in masterplan_data["phases"]:
                phase = self._create_phase(db, masterplan, phase_data, task_number_to_uuid)
                db.add(phase)

            # Update task dependencies (now that all task UUIDs are known)
            self._update_task_dependencies(db, task_number_to_uuid, masterplan_data)

            # Update counts
            masterplan.total_phases = len(masterplan_data["phases"])
            masterplan.total_milestones = sum(
                len(phase.get("milestones", []))
                for phase in masterplan_data["phases"]
            )

            # Calculate correct estimated cost based on actual task complexity
            estimated_cost = self._calculate_estimated_cost(masterplan_data)
            masterplan.estimated_cost_usd = estimated_cost

            db.commit()
            db.refresh(masterplan)

            logger.info(
                "MasterPlan saved to database",
                masterplan_id=str(masterplan.masterplan_id),
                phases=masterplan.total_phases,
                milestones=masterplan.total_milestones,
                tasks=masterplan.total_tasks
            )

            return masterplan.masterplan_id

    def _create_phase(
        self,
        db,
        masterplan: MasterPlan,
        phase_data: Dict,
        task_number_to_uuid: Dict[int, UUID]
    ) -> MasterPlanPhase:
        """Create Phase with Milestones and Tasks."""
        # Map phase_number to PhaseType
        phase_type_map = {
            1: PhaseType.SETUP,
            2: PhaseType.CORE,
            3: PhaseType.POLISH
        }

        phase = MasterPlanPhase(
            masterplan_id=masterplan.masterplan_id,
            phase_type=phase_type_map.get(phase_data["phase_number"], PhaseType.CORE),
            phase_number=phase_data["phase_number"],
            name=phase_data["name"],
            description=phase_data.get("description")
        )

        db.add(phase)
        db.flush()

        # Create Milestones
        for milestone_data in phase_data.get("milestones", []):
            milestone = self._create_milestone(db, phase, milestone_data, task_number_to_uuid)
            db.add(milestone)
            # Count phase tasks
            phase.total_tasks = (phase.total_tasks or 0) + (milestone.total_tasks or 0)
            phase.total_milestones = (phase.total_milestones or 0) + 1

        return phase

    def _create_milestone(
        self,
        db,
        phase: MasterPlanPhase,
        milestone_data: Dict,
        task_number_to_uuid: Dict[int, UUID]
    ) -> MasterPlanMilestone:
        """Create Milestone with Tasks."""
        milestone = MasterPlanMilestone(
            phase_id=phase.phase_id,
            milestone_number=milestone_data["milestone_number"],
            name=milestone_data["name"],
            description=milestone_data.get("description"),
            depends_on_milestones=milestone_data.get("depends_on_milestones", [])
        )

        db.add(milestone)
        db.flush()

        # Create Tasks
        for task_data in milestone_data.get("tasks", []):
            task = self._create_task(db, milestone, task_data)  # Already adds to db and flushes

            # Map task_number → task_id
            task_number_to_uuid[task_data["task_number"]] = task.task_id

            # Count milestone tasks
            milestone.total_tasks = (milestone.total_tasks or 0) + 1

        return milestone

    def _create_task(
        self,
        db,
        milestone: MasterPlanMilestone,
        task_data: Dict
    ) -> MasterPlanTask:
        """Create Task."""
        # Map complexity string to enum
        complexity_map = {
            "low": DBTaskComplexity.LOW,
            "medium": DBTaskComplexity.MEDIUM,
            "high": DBTaskComplexity.HIGH,
            "critical": DBTaskComplexity.CRITICAL
        }

        task = MasterPlanTask(
            milestone_id=milestone.milestone_id,
            task_number=task_data["task_number"],
            name=task_data["name"],
            description=task_data["description"],
            complexity=complexity_map.get(task_data.get("complexity", "medium"), DBTaskComplexity.MEDIUM),
            depends_on_tasks=[],  # Will be updated later with UUIDs
            target_files=task_data.get("target_files", []),
            status=TaskStatus.PENDING
        )

        db.add(task)
        db.flush()  # Get task_id for subtasks

        # Create Subtasks
        for subtask_data in task_data.get("subtasks", []):
            subtask = MasterPlanSubtask(
                task_id=task.task_id,
                subtask_number=subtask_data["subtask_number"],
                name=subtask_data["name"],
                description=subtask_data.get("description", ""),
                status=TaskStatus.PENDING,
                completed=False
            )
            db.add(subtask)

        return task

    def _calculate_estimated_cost(self, masterplan_data: Dict) -> float:
        """Calculate estimated cost based on task complexity AND subtasks.

        Cost per subtask (based on parent task complexity):
        - Low task: $0.02 per subtask (avg 5 subtasks = $0.10)
        - Medium task: $0.05 per subtask (avg 5 subtasks = $0.25)
        - High task: $0.10 per subtask (avg 5 subtasks = $0.50)

        This reflects that the REAL work is in the subtasks, not the task wrapper.
        """
        subtask_cost_map = {
            "low": 0.02,      # Small operations: imports, simple assignments
            "medium": 0.05,   # Business logic, validation, service calls
            "high": 0.10,     # Complex integrations, auth flows, migrations
            "critical": 0.15  # Payment, security, data transformations
        }

        total_cost = 0.0
        task_count = 0
        subtask_count = 0

        for phase_data in masterplan_data.get("phases", []):
            for milestone_data in phase_data.get("milestones", []):
                for task_data in milestone_data.get("tasks", []):
                    complexity = task_data.get("complexity", "medium").lower()
                    subtasks = task_data.get("subtasks", [])
                    num_subtasks = len(subtasks)

                    # If no subtasks, use minimum 3 as fallback
                    if num_subtasks == 0:
                        num_subtasks = 3

                    cost_per_subtask = subtask_cost_map.get(complexity, 0.05)
                    task_cost = num_subtasks * cost_per_subtask
                    total_cost += task_cost

                    task_count += 1
                    subtask_count += num_subtasks

        logger.info(
            f"Estimated cost calculation: {task_count} tasks, {subtask_count} subtasks, ${total_cost:.2f}"
        )
        return round(total_cost, 2)

    def _update_task_dependencies(
        self,
        db,
        task_number_to_uuid: Dict[int, UUID],
        masterplan_data: Dict
    ):
        """Update task dependencies with actual UUIDs."""
        for phase_data in masterplan_data["phases"]:
            for milestone_data in phase_data.get("milestones", []):
                for task_data in milestone_data.get("tasks", []):
                    task_number = task_data["task_number"]
                    depends_on_numbers = task_data.get("depends_on_tasks", [])

                    if depends_on_numbers:
                        task_uuid = task_number_to_uuid[task_number]
                        task = db.query(MasterPlanTask).filter(
                            MasterPlanTask.task_id == task_uuid
                        ).first()

                        if task:
                            # Convert task numbers to UUIDs
                            task.depends_on_tasks = [
                                str(task_number_to_uuid[dep_num])
                                for dep_num in depends_on_numbers
                                if dep_num in task_number_to_uuid
                            ]

    def get_masterplan(self, masterplan_id: UUID) -> Optional[MasterPlan]:
        """
        Retrieve MasterPlan by ID.

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            MasterPlan or None
        """
        with get_db_context() as db:
            masterplan = db.query(MasterPlan).filter(
                MasterPlan.masterplan_id == masterplan_id
            ).first()

            return masterplan
