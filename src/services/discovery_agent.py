"""
Discovery Agent - DDD Analysis

Performs Domain-Driven Design discovery from user requirements.

Flow:
1. User provides project description
2. Agent conducts DDD analysis (Sonnet 4.5)
3. Identifies: domain, bounded contexts, aggregates, entities, value objects, events, services
4. Saves DiscoveryDocument to PostgreSQL
5. Returns discovery_id for MasterPlan generation

Cost: ~$0.09 per discovery (Sonnet 4.5)
"""

import json
import time
from typing import Dict, Any, Optional
from uuid import UUID

from src.llm import EnhancedAnthropicClient, TaskType, TaskComplexity
from src.models.masterplan import DiscoveryDocument
from src.config.database import get_db_context
from src.observability import get_logger
from src.observability.metrics_collector import MetricsCollector
from src.websocket import WebSocketManager

logger = get_logger("discovery_agent")


# DDD Discovery System Prompt
DISCOVERY_SYSTEM_PROMPT = """You are an expert software architect specializing in Domain-Driven Design (DDD).

Your task is to analyze user requirements and conduct a thorough DDD discovery session.

## Your Analysis Must Identify:

1. **Domain**: The core business domain and problem space
2. **Bounded Contexts**: Logical boundaries within the domain (2-5 contexts)
3. **Aggregates**: Clusters of domain objects treated as a single unit
4. **Entities**: Objects with unique identity (Users, Orders, Products, etc.)
5. **Value Objects**: Objects defined by attributes without identity (Email, Money, Address)
6. **Domain Events**: Significant events in the domain (UserRegistered, OrderPlaced, etc.)
7. **Services**: Domain services and application services

## Output Format (JSON):

```json
{
  "domain": "Name of the domain",
  "bounded_contexts": [
    {
      "name": "Context Name",
      "description": "What this context handles",
      "responsibilities": ["responsibility1", "responsibility2"]
    }
  ],
  "aggregates": [
    {
      "name": "Aggregate Name",
      "root_entity": "Root Entity Name",
      "entities": ["Entity1", "Entity2"],
      "value_objects": ["ValueObject1", "ValueObject2"],
      "bounded_context": "Which context this belongs to"
    }
  ],
  "value_objects": [
    {
      "name": "ValueObject Name",
      "attributes": ["attr1", "attr2"],
      "validation_rules": ["rule1", "rule2"]
    }
  ],
  "domain_events": [
    {
      "name": "EventName",
      "trigger": "What causes this event",
      "data": ["field1", "field2"],
      "subscribers": ["Service that listens to this"]
    }
  ],
  "services": [
    {
      "name": "Service Name",
      "type": "domain|application",
      "responsibilities": ["What it does"]
    }
  ],
  "assumptions": ["Assumption 1", "Assumption 2"],
  "clarifications_needed": ["Question 1", "Question 2"],
  "risk_factors": ["Risk 1", "Risk 2"]
}
```

## Guidelines:

- Be thorough but pragmatic - focus on essential domain concepts
- Identify 2-5 bounded contexts (not too granular for MVP)
- Each aggregate should have 1 root entity
- Domain events should capture state changes
- Separate domain services (business logic) from application services (orchestration)
- Note assumptions you're making
- Ask clarifying questions if critical information is missing
- Highlight risks or complexity areas

**IMPORTANT**: Return ONLY valid JSON, no markdown, no explanations outside the JSON.
"""


class DiscoveryAgent:
    """
    Discovery Agent for DDD analysis.

    Usage:
        agent = DiscoveryAgent()
        discovery_id = await agent.conduct_discovery(
            user_request="Build a task management system...",
            session_id="session_123",
            user_id="user_456"
        )
    """

    def __init__(
        self,
        llm_client: Optional[EnhancedAnthropicClient] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize Discovery Agent.

        Args:
            llm_client: LLM client (creates new if not provided)
            metrics_collector: Metrics collector
            websocket_manager: WebSocket manager for real-time progress updates (optional)
        """
        self.llm = llm_client or EnhancedAnthropicClient()
        self.metrics = metrics_collector or MetricsCollector()
        self.ws_manager = websocket_manager

        logger.info(
            f"DiscoveryAgent initialized with websocket_manager: {websocket_manager is not None}, "
            f"type: {type(websocket_manager).__name__ if websocket_manager else 'None'}"
        )

    async def conduct_discovery(
        self,
        user_request: str,
        session_id: str,
        user_id: str
    ) -> UUID:
        """
        Conduct DDD discovery from user requirements.

        Args:
            user_request: User's project description
            session_id: Session identifier
            user_id: User identifier

        Returns:
            discovery_id: UUID of created DiscoveryDocument

        Raises:
            ValueError: If user_request is empty or invalid
            RuntimeError: If discovery fails
        """
        overall_start_time = time.time()

        # Validate input
        if not user_request or not user_request.strip():
            raise ValueError("user_request cannot be empty")

        logger.info(
            "Starting DDD discovery",
            session_id=session_id,
            user_id=user_id,
            request_length=len(user_request)
        )

        # Record start metric
        self.metrics.increment_counter(
            "discovery_requests_total",
            labels={"session_id": session_id},
            help_text="Total discovery requests"
        )

        # Emit generation start event
        logger.info(f"🔍 [DEBUG] About to check ws_manager: {self.ws_manager is not None}")
        if self.ws_manager:
            logger.info(f"🚀 Emitting discovery_generation_start WebSocket event to session_id={session_id}")
            await self.ws_manager.emit_discovery_generation_start(
                session_id=session_id,
                estimated_tokens=8000,
                estimated_duration_seconds=30,
                estimated_cost_usd=0.09
            )
            logger.info(f"✅ Successfully emitted discovery_generation_start")
        else:
            logger.warning(f"⚠️  [DEBUG] ws_manager is None! Cannot emit discovery_generation_start")

        try:
            # Generate discovery with LLM (always Sonnet 4.5 for discovery)
            discovery_json = await self._generate_discovery(user_request, session_id)

            # Parse discovery result
            discovery_data = self._parse_discovery(discovery_json)

            # Emit granular discovery events for detailed progress display
            if self.ws_manager:
                # Emit domain discovered
                await self.ws_manager.emit_discovery_entity_discovered(
                    session_id=session_id,
                    entity_type="domain",
                    name=discovery_data.get("domain", "Unknown"),
                    count=1
                )

                # Emit bounded contexts discovered
                bounded_contexts = discovery_data.get("bounded_contexts", [])
                for i, context in enumerate(bounded_contexts, 1):
                    await self.ws_manager.emit_discovery_entity_discovered(
                        session_id=session_id,
                        entity_type="bounded_context",
                        name=context.get("name", f"Context {i}"),
                        count=i
                    )

                # Emit aggregates discovered
                aggregates = discovery_data.get("aggregates", [])
                for i, aggregate in enumerate(aggregates, 1):
                    await self.ws_manager.emit_discovery_entity_discovered(
                        session_id=session_id,
                        entity_type="aggregate",
                        name=aggregate.get("name", f"Aggregate {i}"),
                        count=i
                    )

                # Emit entities discovered (from value objects and domain events)
                value_objects = discovery_data.get("value_objects", [])
                domain_events = discovery_data.get("domain_events", [])
                total_entities = len(value_objects) + len(domain_events)

                if total_entities > 0:
                    await self.ws_manager.emit_discovery_entity_discovered(
                        session_id=session_id,
                        entity_type="entity",
                        name=f"{total_entities} Value Objects & Domain Events",
                        count=total_entities
                    )

            # Emit parsing complete event
            if self.ws_manager:
                total_entities = (
                    len(discovery_data.get("aggregates", [])) +
                    len(discovery_data.get("value_objects", [])) +
                    len(discovery_data.get("domain_events", []))
                )
                await self.ws_manager.emit_discovery_parsing_complete(
                    session_id=session_id,
                    domain=discovery_data.get("domain", "Unknown"),
                    total_bounded_contexts=len(discovery_data.get("bounded_contexts", [])),
                    total_aggregates=len(discovery_data.get("aggregates", [])),
                    total_entities=total_entities
                )

            # Emit saving start event
            if self.ws_manager:
                total_entities = (
                    len(discovery_data.get("bounded_contexts", [])) +
                    len(discovery_data.get("aggregates", [])) +
                    len(discovery_data.get("value_objects", [])) +
                    len(discovery_data.get("domain_events", [])) +
                    len(discovery_data.get("services", []))
                )
                await self.ws_manager.emit_discovery_saving_start(
                    session_id=session_id,
                    total_entities=total_entities
                )

            # Save to database
            discovery_id = self._save_discovery(
                user_request=user_request,
                session_id=session_id,
                user_id=user_id,
                discovery_data=discovery_data,
                llm_model=discovery_json.get("model"),
                llm_cost=discovery_json.get("cost_usd")
            )

            # Record success
            self.metrics.increment_counter(
                "discovery_success_total",
                labels={"session_id": session_id},
                help_text="Successful discoveries"
            )

            total_duration = time.time() - overall_start_time

            # Emit generation complete event
            if self.ws_manager:
                total_entities = (
                    len(discovery_data.get("aggregates", [])) +
                    len(discovery_data.get("value_objects", [])) +
                    len(discovery_data.get("domain_events", []))
                )
                await self.ws_manager.emit_discovery_generation_complete(
                    session_id=session_id,
                    discovery_id=str(discovery_id),
                    domain=discovery_data.get("domain", "Unknown"),
                    total_bounded_contexts=len(discovery_data.get("bounded_contexts", [])),
                    total_aggregates=len(discovery_data.get("aggregates", [])),
                    total_entities=total_entities,
                    generation_cost_usd=discovery_json.get("cost_usd", 0.0),
                    duration_seconds=total_duration
                )

            logger.info(
                "Discovery completed successfully",
                discovery_id=str(discovery_id),
                session_id=session_id,
                domain=discovery_data.get("domain"),
                bounded_contexts_count=len(discovery_data.get("bounded_contexts", [])),
                aggregates_count=len(discovery_data.get("aggregates", []))
            )

            return discovery_id

        except Exception as e:
            # Record failure
            self.metrics.increment_counter(
                "discovery_failures_total",
                labels={"session_id": session_id, "error_type": type(e).__name__},
                help_text="Failed discoveries"
            )

            logger.error(
                "Discovery failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise RuntimeError(f"Discovery failed: {str(e)}") from e

    async def _generate_discovery(self, user_request: str, session_id: str) -> Dict[str, Any]:
        """
        Generate discovery using LLM.

        Args:
            user_request: User's project description
            session_id: Session ID for WebSocket progress updates

        Returns:
            Dict with discovery JSON and metadata
        """
        start_time = time.time()

        # Build prompt
        variable_prompt = f"""Analyze the following project requirements and conduct a DDD discovery:

## User Requirements:
{user_request}

Provide a complete DDD analysis in the specified JSON format."""

        # Emit token progress updates (simulated since we don't have streaming visibility)
        if self.ws_manager:
            # Start progress monitoring task
            import asyncio

            estimated_total_tokens = 8000
            estimated_duration = 90  # seconds (LLM generation typically takes 30-60s)
            progress_interval = 3  # seconds

            async def emit_progress():
                """Emit periodic progress updates during LLM generation"""
                elapsed = 0
                phases = [
                    "Analyzing domain concepts...",
                    "Identifying bounded contexts...",
                    "Discovering aggregates...",
                    "Mapping entities and value objects...",
                    "Defining domain events...",
                    "Finalizing services..."
                ]

                # Emit initial progress immediately to show modal is working
                await self.ws_manager.emit_discovery_tokens_progress(
                    session_id=session_id,
                    tokens_received=100,
                    estimated_total=estimated_total_tokens,
                    current_phase=phases[0]
                )

                while elapsed < estimated_duration:
                    await asyncio.sleep(progress_interval)
                    elapsed += progress_interval

                    # Conservative progress (cap at 90% until done)
                    progress_ratio = min(elapsed / estimated_duration, 0.90)
                    tokens_received = int(estimated_total_tokens * progress_ratio)

                    phase_index = min(int((elapsed / estimated_duration) * len(phases)), len(phases) - 1)
                    current_phase = phases[phase_index]

                    await self.ws_manager.emit_discovery_tokens_progress(
                        session_id=session_id,
                        tokens_received=tokens_received,
                        estimated_total=estimated_total_tokens,
                        current_phase=current_phase
                    )

            # Start progress task in background
            progress_task = asyncio.create_task(emit_progress())

        # Generate with caching (no cacheable context for discovery - it's always unique)
        response = await self.llm.generate_with_caching(
            task_type=TaskType.DISCOVERY,  # Always uses Sonnet 4.5
            complexity=TaskComplexity.HIGH,
            cacheable_context={
                "system_prompt": DISCOVERY_SYSTEM_PROMPT
            },
            variable_prompt=variable_prompt,
            max_tokens=8000,
            temperature=0.7
        )

        # Let progress task complete naturally instead of canceling
        # This ensures all progress events are emitted and delivered to clients
        if self.ws_manager:
            try:
                # Wait for progress task to complete (with timeout to avoid hanging)
                await asyncio.wait_for(progress_task, timeout=2)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Task may have already completed or timed out naturally
                pass

        duration = time.time() - start_time

        logger.info(
            "Discovery LLM generation complete",
            model=response["model"],
            cost_usd=response["cost_usd"],
            duration_seconds=duration,
            input_tokens=response["usage"]["input_tokens"],
            output_tokens=response["usage"]["output_tokens"]
        )

        return {
            "content": response["content"],
            "model": response["model"],
            "cost_usd": response["cost_usd"],
            "usage": response["usage"],
            "duration_seconds": duration
        }

    def _parse_discovery(self, discovery_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate discovery JSON.

        Args:
            discovery_response: Response from LLM

        Returns:
            Parsed discovery data

        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        content = discovery_response["content"]

        # Try to extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Parse JSON
        try:
            discovery_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse discovery JSON", error=str(e), content=content[:500])
            raise ValueError(f"Invalid JSON from LLM: {str(e)}") from e

        # Validate required fields
        required_fields = ["domain", "bounded_contexts", "aggregates"]
        missing_fields = [f for f in required_fields if f not in discovery_data]

        if missing_fields:
            raise ValueError(f"Discovery missing required fields: {missing_fields}")

        # Ensure all fields exist (with defaults)
        discovery_data.setdefault("value_objects", [])
        discovery_data.setdefault("domain_events", [])
        discovery_data.setdefault("services", [])
        discovery_data.setdefault("assumptions", [])
        discovery_data.setdefault("clarifications_needed", [])
        discovery_data.setdefault("risk_factors", [])

        logger.debug(
            "Discovery parsed successfully",
            domain=discovery_data["domain"],
            bounded_contexts=len(discovery_data["bounded_contexts"]),
            aggregates=len(discovery_data["aggregates"])
        )

        return discovery_data

    def _save_discovery(
        self,
        user_request: str,
        session_id: str,
        user_id: str,
        discovery_data: Dict[str, Any],
        llm_model: str,
        llm_cost: float
    ) -> UUID:
        """
        Save discovery to database.

        Args:
            user_request: Original user request
            session_id: Session ID
            user_id: User ID
            discovery_data: Parsed discovery data
            llm_model: Model used
            llm_cost: Cost in USD

        Returns:
            discovery_id: UUID of saved document
        """
        with get_db_context() as db:
            # Create DiscoveryDocument
            discovery = DiscoveryDocument(
                session_id=session_id,
                user_id=user_id,
                user_request=user_request,
                domain=discovery_data["domain"],
                bounded_contexts=discovery_data["bounded_contexts"],
                aggregates=discovery_data["aggregates"],
                value_objects=discovery_data["value_objects"],
                domain_events=discovery_data["domain_events"],
                services=discovery_data["services"],
                assumptions=discovery_data.get("assumptions"),
                clarifications_needed=discovery_data.get("clarifications_needed"),
                risk_factors=discovery_data.get("risk_factors"),
                llm_model=llm_model,
                llm_cost_usd=llm_cost
            )

            db.add(discovery)
            db.commit()
            db.refresh(discovery)

            logger.info(
                "Discovery saved to database",
                discovery_id=str(discovery.discovery_id),
                session_id=session_id
            )

            return discovery.discovery_id

    def get_discovery(self, discovery_id: UUID) -> Optional[DiscoveryDocument]:
        """
        Retrieve discovery by ID.

        Args:
            discovery_id: Discovery UUID

        Returns:
            DiscoveryDocument or None if not found
        """
        with get_db_context() as db:
            discovery = db.query(DiscoveryDocument).filter(
                DiscoveryDocument.discovery_id == discovery_id
            ).first()

            return discovery

    def get_discovery_by_session(self, session_id: str) -> Optional[DiscoveryDocument]:
        """
        Get most recent discovery for session.

        Args:
            session_id: Session ID

        Returns:
            Most recent DiscoveryDocument or None
        """
        with get_db_context() as db:
            discovery = db.query(DiscoveryDocument).filter(
                DiscoveryDocument.session_id == session_id
            ).order_by(DiscoveryDocument.created_at.desc()).first()

            return discovery

