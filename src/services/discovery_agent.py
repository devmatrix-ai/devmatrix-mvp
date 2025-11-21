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
        import asyncio
        overall_start_time = time.time()

        # Capture the running event loop for use in sync callbacks
        if self.ws_manager:
            try:
                self.ws_manager.event_loop = asyncio.get_running_loop()
                logger.info(f"✅ Captured event loop for progress callbacks")
            except RuntimeError:
                logger.warning(f"Could not capture event loop for progress callbacks")

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
        Generate discovery using LLM with granular DDD entity streaming.

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

        # Track discovered entities for relationship detection
        discovered_entities = {
            "bounded_contexts": [],
            "aggregates": [],
            "services": []
        }

        async def entity_discovered_callback(entity: Dict[str, Any]):
            """
            Callback for when a complete entity JSON is discovered in the stream.
            Detects entity type and emits appropriate WebSocket events.
            """
            try:
                # Detect entity type by presence of characteristic keys
                if "bounded_contexts" in entity:
                    # This is a bounded_contexts array
                    for i, context in enumerate(entity["bounded_contexts"], 1):
                        if self.ws_manager:
                            await self.ws_manager.emit_discovery_entity_streaming(
                                session_id=session_id,
                                entity_type="bounded_context",
                                name=context.get("name", f"Context {i}"),
                                properties={
                                    "description": context.get("description", ""),
                                    "responsibilities": context.get("responsibilities", [])
                                },
                                chunk_index=i
                            )
                        discovered_entities["bounded_contexts"].append(context)

                elif "aggregates" in entity:
                    # This is an aggregates array
                    for i, aggregate in enumerate(entity["aggregates"], 1):
                        if self.ws_manager:
                            await self.ws_manager.emit_discovery_entity_streaming(
                                session_id=session_id,
                                entity_type="aggregate",
                                name=aggregate.get("name", f"Aggregate {i}"),
                                properties={
                                    "root_entity": aggregate.get("root_entity", ""),
                                    "entities": aggregate.get("entities", []),
                                    "value_objects": aggregate.get("value_objects", []),
                                    "bounded_context": aggregate.get("bounded_context", "")
                                },
                                chunk_index=i
                            )
                        discovered_entities["aggregates"].append(aggregate)

                elif "value_objects" in entity:
                    # This is a value_objects array
                    for i, vo in enumerate(entity["value_objects"], 1):
                        if self.ws_manager:
                            await self.ws_manager.emit_discovery_entity_streaming(
                                session_id=session_id,
                                entity_type="value_object",
                                name=vo.get("name", f"ValueObject {i}"),
                                properties={
                                    "attributes": vo.get("attributes", []),
                                    "validation_rules": vo.get("validation_rules", [])
                                },
                                chunk_index=i
                            )

                elif "domain_events" in entity:
                    # This is a domain_events array
                    for i, event in enumerate(entity["domain_events"], 1):
                        if self.ws_manager:
                            await self.ws_manager.emit_discovery_entity_streaming(
                                session_id=session_id,
                                entity_type="domain_event",
                                name=event.get("name", f"Event {i}"),
                                properties={
                                    "trigger": event.get("trigger", ""),
                                    "data": event.get("data", []),
                                    "subscribers": event.get("subscribers", [])
                                },
                                chunk_index=i
                            )

                elif "services" in entity:
                    # This is a services array
                    for i, service in enumerate(entity["services"], 1):
                        if self.ws_manager:
                            await self.ws_manager.emit_discovery_entity_streaming(
                                session_id=session_id,
                                entity_type="service",
                                name=service.get("name", f"Service {i}"),
                                properties={
                                    "type": service.get("type", "domain"),
                                    "responsibilities": service.get("responsibilities", [])
                                },
                                chunk_index=i
                            )
                        discovered_entities["services"].append(service)

                elif "domain" in entity:
                    # This is the top-level domain object
                    if self.ws_manager:
                        await self.ws_manager.emit_discovery_entity_streaming(
                            session_id=session_id,
                            entity_type="domain",
                            name=entity.get("domain", "Unknown Domain"),
                            properties={
                                "assumptions": entity.get("assumptions", []),
                                "clarifications_needed": entity.get("clarifications_needed", []),
                                "risk_factors": entity.get("risk_factors", [])
                            },
                            chunk_index=0
                        )

            except Exception as e:
                logger.error(f"Error in entity_discovered_callback: {e}")

        def progress_callback(progress_info: Dict[str, Any]):
            """
            Callback for streaming progress updates.
            Emits real-time progress to WebSocket SYNCHRONOUSLY.
            """
            logger.info(f"📊 PROGRESS_CALLBACK: chunk_count={progress_info.get('chunk_count')}, objects={progress_info.get('objects_found')}, ws_manager={bool(self.ws_manager)}")
            if self.ws_manager:
                try:
                    # Emit synchronously without async/await
                    logger.info(f"📊 About to emit_streaming_progress_sync...")
                    self.ws_manager.emit_streaming_progress_sync(
                        session_id=session_id,
                        tokens_received=progress_info.get("chunk_count", 0) * 4,  # Rough estimate
                        estimated_total=8000,
                        content_preview="Discovering DDD entities...",
                        entities_found=progress_info.get("objects_found", 0)
                    )
                    logger.info(f"📊 emit_streaming_progress_sync completed")
                except Exception as e:
                    logger.error(f"Error emitting progress: {e}", exc_info=True)

        # Stream discovery with callbacks for real-time entity extraction
        response = await self.llm.stream_with_callbacks(
            model="claude-opus-4-1-20250805",
            messages=[
                {
                    "role": "user",
                    "content": variable_prompt
                }
            ],
            system=DISCOVERY_SYSTEM_PROMPT,
            max_tokens=8000,
            temperature=0.0,  # Deterministic mode
            entity_callback=entity_discovered_callback,
            progress_callback=progress_callback,
            target_keys=["bounded_contexts", "aggregates", "value_objects", "domain_events", "services", "domain"]
        )

        # Detect relationships between discovered entities
        await self._detect_and_emit_relationships(session_id, discovered_entities)

        # Detect architectural patterns
        await self._detect_and_emit_patterns(session_id, discovered_entities)

        duration = time.time() - start_time

        logger.info(
            "Discovery LLM generation complete",
            model="claude-opus-4-1-20250805",
            duration_seconds=duration,
            input_tokens=response["usage"]["input_tokens"],
            output_tokens=response["usage"]["output_tokens"]
        )

        return {
            "content": response["full_text"],
            "model": "claude-opus-4-1-20250805",
            "cost_usd": (response["usage"]["input_tokens"] * 0.003 + response["usage"]["output_tokens"] * 0.015) / 1000,
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

    async def _detect_and_emit_relationships(
        self,
        session_id: str,
        discovered_entities: Dict[str, Any]
    ) -> None:
        """
        Detect relationships between discovered entities and emit WebSocket events.

        Analyzes aggregates and services to find dependencies and publishes events.

        Args:
            session_id: Session ID for WebSocket events
            discovered_entities: Dictionary of discovered DDD entities
        """
        if not self.ws_manager:
            return

        try:
            # Extract aggregates and services for relationship analysis
            aggregates = discovered_entities.get("aggregates", [])
            services = discovered_entities.get("services", [])

            # Detect aggregate dependencies
            for agg1 in aggregates:
                agg1_name = agg1.get("name", "")
                for agg2 in aggregates:
                    if agg1_name == agg2.get("name"):
                        continue
                    agg2_name = agg2.get("name", "")

                    # Simple heuristic: check if agg2 name appears in agg1 entities/value_objects
                    agg1_content = str(agg1.get("entities", [])) + str(agg1.get("value_objects", []))
                    if agg2_name.lower() in agg1_content.lower():
                        await self.ws_manager.emit_discovery_relationship_found(
                            session_id=session_id,
                            from_entity=agg1_name,
                            to_entity=agg2_name,
                            relationship_type="depends_on",
                            details={"type": "aggregate_dependency"}
                        )

            # Detect service-aggregate relationships
            for service in services:
                service_name = service.get("name", "")
                service_responsibilities = str(service.get("responsibilities", []))

                for agg in aggregates:
                    agg_name = agg.get("name", "")
                    # Check if aggregate name appears in service responsibilities
                    if agg_name.lower() in service_responsibilities.lower():
                        await self.ws_manager.emit_discovery_relationship_found(
                            session_id=session_id,
                            from_entity=service_name,
                            to_entity=agg_name,
                            relationship_type="orchestrates",
                            details={"type": "service_aggregate_relationship"}
                        )

            logger.info(f"Relationship detection completed for session {session_id}")

        except Exception as e:
            logger.error(f"Error detecting relationships: {e}")

    async def _detect_and_emit_patterns(
        self,
        session_id: str,
        discovered_entities: Dict[str, Any]
    ) -> None:
        """
        Detect architectural patterns in the discovery and emit WebSocket events.

        Identifies common DDD patterns like Event Sourcing, Saga, CQRS, etc.

        Args:
            session_id: Session ID for WebSocket events
            discovered_entities: Dictionary of discovered DDD entities
        """
        if not self.ws_manager:
            return

        try:
            services = discovered_entities.get("services", [])
            aggregates = discovered_entities.get("aggregates", [])
            affected_entities = []

            # Pattern 1: Event Sourcing - Many domain events with aggregate dependencies
            domain_event_count = len(discovered_entities.get("domain_events", []))
            if domain_event_count > 5:
                affected_entities = [f"Domain has {domain_event_count} events"]
                await self.ws_manager.emit_discovery_pattern_detected(
                    session_id=session_id,
                    pattern="event_sourcing_candidate",
                    confidence=0.6 if domain_event_count > 8 else 0.4,
                    affected_entities=affected_entities,
                    description=f"High event volume ({domain_event_count} domain events) suggests potential Event Sourcing pattern"
                )

            # Pattern 2: CQRS - Separate read/write services
            read_services = [s for s in services if "read" in s.get("name", "").lower() or "query" in s.get("name", "").lower()]
            write_services = [s for s in services if "write" in s.get("name", "").lower() or "command" in s.get("name", "").lower()]

            if read_services and write_services:
                affected_entities = [s.get("name", "") for s in read_services + write_services]
                await self.ws_manager.emit_discovery_pattern_detected(
                    session_id=session_id,
                    pattern="cqrs",
                    confidence=0.8,
                    affected_entities=affected_entities,
                    description="CQRS pattern identified with separate read and write services"
                )

            # Pattern 3: Saga - Services with coordinating relationships
            coordinating_services = [s for s in services if "coordinator" in s.get("name", "").lower() or "orchestrator" in s.get("name", "").lower()]
            if coordinating_services and len(services) > 3:
                affected_entities = [s.get("name", "") for s in coordinating_services]
                await self.ws_manager.emit_discovery_pattern_detected(
                    session_id=session_id,
                    pattern="saga",
                    confidence=0.7,
                    affected_entities=affected_entities,
                    description="Saga pattern identified with coordinating services across multiple aggregates"
                )

            # Pattern 4: Domain Events - Multiple domain events suggest event-driven architecture
            if domain_event_count > 3:
                affected_entities = [e.get("name", "") for e in discovered_entities.get("domain_events", [])[:5]]
                await self.ws_manager.emit_discovery_pattern_detected(
                    session_id=session_id,
                    pattern="event_driven",
                    confidence=0.7,
                    affected_entities=affected_entities,
                    description=f"Event-driven architecture pattern with {domain_event_count} domain events"
                )

            logger.info(f"Pattern detection completed for session {session_id}")

        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")

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

