"""
WebSocket Manager

Manages WebSocket connections and event emissions for real-time updates.
Provides helper methods for MasterPlan generation progress updates.
"""

import socketio
from typing import Dict, Any, Optional
from src.observability import get_logger

logger = get_logger("websocket_manager")


class WebSocketManager:
    """
    WebSocket manager for real-time event emissions.

    Usage:
        # In API/Service layer
        from src.websocket import WebSocketManager

        ws_manager = WebSocketManager(sio)

        # Emit to specific session
        await ws_manager.emit_to_session(
            session_id="session_123",
            event="masterplan_generation_start",
            data={"estimated_tokens": 17000}
        )

        # Emit to chat room
        await ws_manager.emit_to_chat(
            conversation_id="conv_123",
            event="message",
            data={"content": "..."}
        )
    """

    def __init__(self, sio_server: Optional[socketio.AsyncServer] = None):
        """
        Initialize WebSocket manager.

        Args:
            sio_server: Socket.IO server instance (optional, will be set later if None)
        """
        self.sio = sio_server
        self.event_loop = None  # Will be set dynamically when needed
        # Store recent events for catch-up (max 100 events per session)
        self.event_history: Dict[str, list] = {}
        logger.info("WebSocketManager initialized")

    def set_sio_server(self, sio_server: socketio.AsyncServer):
        """
        Set Socket.IO server (used when creating manager before sio is available).

        Args:
            sio_server: Socket.IO server instance
        """
        self.sio = sio_server
        logger.info("Socket.IO server set")

    def store_event(self, session_id: str, event_name: str, event_data: Dict[str, Any]):
        """
        Store event in history for catch-up requests.

        Events are stored per session_id to be replayed when clients request catch-up.
        Each session keeps max 100 events to prevent unbounded memory growth.

        Args:
            session_id: Session ID (discovery or masterplan ID)
            event_name: Name of the event (e.g., 'discovery_tokens_progress')
            event_data: Event payload dictionary
        """
        import time

        if session_id not in self.event_history:
            self.event_history[session_id] = []

        # Add event with timestamp
        self.event_history[session_id].append({
            'event': event_name,
            'data': event_data,
            'timestamp': time.time()
        })

        # Keep only last 100 events per session to prevent memory bloat
        if len(self.event_history[session_id]) > 100:
            self.event_history[session_id] = self.event_history[session_id][-100:]

        print(f"🔴 STORED: {event_name} for {session_id} - total: {len(self.event_history[session_id])}")
        logger.info(
            f"📡 [STORED] Event for catch-up - session {session_id} has {len(self.event_history[session_id])} events"
        )

    async def emit_to_session(
        self,
        session_id: str,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Emit event to a specific session (by sid).

        Emits to TWO rooms for resilience against page refreshes:
        1. Direct sid room (ephemeral, current connection)
        2. Persistent discovery/masterplan room (survives refresh)

        Args:
            session_id: Session ID (Socket.IO sid)
            event: Event name
            data: Event data
        """
        if not self.sio:
            raise RuntimeError(
                f"Socket.IO server not initialized - cannot emit critical event: {event}. "
                f"This indicates a configuration error or initialization failure. "
                f"WebSocket events are essential for real-time progress updates."
            )

        try:
            # Emit to direct sid room (current connection)
            await self.sio.emit(event, data, room=session_id)

            # ALSO emit to persistent discovery room for reconnected clients
            # This allows clients to receive updates even after page refresh
            try:
                persistent_room = f"discovery_{session_id}"
                await self.sio.emit(event, data, room=persistent_room)
            except Exception:
                # If persistent room emission fails, continue anyway
                # (client on current sid already received it)
                pass

            logger.info(
                f"✅ Emitted event to session (both sid and persistent discovery room)",
                event=event,
                session_id=session_id,
                data_keys=list(data.keys())
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to emit event to session",
                event=event,
                session_id=session_id,
                error=str(e),
                exc_info=True
            )

    async def emit_to_chat(
        self,
        conversation_id: str,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Emit event to chat room with resilience against reconnections.

        Args:
            conversation_id: Conversation ID
            event: Event name
            data: Event data
        """
        if not self.sio:
            raise RuntimeError(
                f"Socket.IO server not initialized - cannot emit critical event: {event}. "
                f"This indicates a configuration error or initialization failure. "
                f"WebSocket events are essential for real-time progress updates."
            )

        try:
            room = f"chat_{conversation_id}"
            await self.sio.emit(event, data, room=room)
            logger.debug(
                f"Emitted event to chat",
                event=event,
                conversation_id=conversation_id,
                data_keys=list(data.keys())
            )
        except Exception as e:
            logger.error(
                f"Failed to emit event to chat",
                event=event,
                conversation_id=conversation_id,
                error=str(e)
            )

    async def emit_to_execution(
        self,
        execution_id: str,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Emit event to execution room.

        Args:
            execution_id: Execution ID
            event: Event name
            data: Event data
        """
        if not self.sio:
            raise RuntimeError(
                f"Socket.IO server not initialized - cannot emit critical event: {event}. "
                f"This indicates a configuration error or initialization failure. "
                f"WebSocket events are essential for real-time progress updates."
            )

        try:
            room = f"execution_{execution_id}"
            await self.sio.emit(event, data, room=room)
            logger.debug(
                f"Emitted event to execution",
                event=event,
                execution_id=execution_id,
                data_keys=list(data.keys())
            )
        except Exception as e:
            logger.error(
                f"Failed to emit event to execution",
                event=event,
                execution_id=execution_id,
                error=str(e)
            )

    async def emit_to_masterplan(
        self,
        masterplan_id: str,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Emit event to masterplan room.

        Args:
            masterplan_id: MasterPlan ID
            event: Event name
            data: Event data
        """
        if not self.sio:
            raise RuntimeError(
                f"Socket.IO server not initialized - cannot emit critical event: {event}. "
                f"This indicates a configuration error or initialization failure. "
                f"WebSocket events are essential for real-time progress updates."
            )

        try:
            room = f"masterplan_{masterplan_id}"
            await self.sio.emit(event, data, room=room)
            logger.debug(
                f"Emitted event to masterplan",
                event=event,
                masterplan_id=masterplan_id,
                data_keys=list(data.keys())
            )
        except Exception as e:
            logger.error(
                f"Failed to emit event to masterplan",
                event=event,
                masterplan_id=masterplan_id,
                error=str(e)
            )

    # =========================================================================
    # MasterPlan Generation Progress Events
    # =========================================================================

    async def emit_masterplan_generation_start(
        self,
        session_id: str,
        discovery_id: str,
        estimated_tokens: int = 17000,
        estimated_duration_seconds: int = 90,
        estimated_cost_usd: float = 0.25,
        masterplan_id: Optional[str] = None
    ):
        """
        Emit MasterPlan generation start event.

        Args:
            session_id: Session ID
            discovery_id: Discovery document ID
            estimated_tokens: Estimated total tokens (~17000)
            estimated_duration_seconds: Estimated duration in seconds (~90)
            estimated_cost_usd: Estimated cost in USD (~0.25 for Sonnet 4.5)
            masterplan_id: MasterPlan ID if already created (optional)
        """
        data = {
            "discovery_id": discovery_id,
            "session_id": session_id,
            "estimated_tokens": estimated_tokens,
            "estimated_duration_seconds": estimated_duration_seconds,
            "estimated_cost_usd": estimated_cost_usd
        }
        if masterplan_id:
            data["masterplan_id"] = masterplan_id

        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_generation_start",
            data=data
        )

    async def emit_masterplan_tokens_progress(
        self,
        session_id: str,
        tokens_received: int,
        estimated_total: int,
        current_phase: str
    ):
        """
        Emit MasterPlan token progress event.

        Args:
            session_id: Session ID
            tokens_received: Tokens received so far
            estimated_total: Estimated total tokens
            current_phase: Current phase description
        """
        # Conservative percentage (cap at 95%)
        raw_percentage = int((tokens_received / estimated_total) * 100) if estimated_total > 0 else 0
        percentage = min(raw_percentage, 95)

        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_tokens_progress",
            data={
                "session_id": session_id,
                "tokens_received": tokens_received,
                "estimated_total": estimated_total,
                "percentage": percentage,
                "current_phase": current_phase
            }
        )

    async def emit_masterplan_entity_discovered(
        self,
        session_id: str,
        entity_type: str,  # "phase", "milestone", "task"
        count: int,
        name: Optional[str] = None,
        parent: Optional[str] = None
    ):
        """
        Emit MasterPlan entity discovered event.

        Args:
            session_id: Session ID
            entity_type: Type of entity ("phase", "milestone", "task")
            count: Total count of this entity type discovered so far
            name: Name of the entity (optional)
            parent: Parent entity name (optional)
        """
        data = {
            "session_id": session_id,
            "type": entity_type,
            "count": count
        }

        if name:
            data["name"] = name
        if parent:
            data["parent"] = parent

        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_entity_discovered",
            data=data
        )

    async def emit_masterplan_parsing_complete(
        self,
        session_id: str,
        total_phases: int,
        total_milestones: int,
        total_tasks: int
    ):
        """
        Emit MasterPlan parsing complete event.

        Args:
            session_id: Session ID
            total_phases: Total number of phases
            total_milestones: Total number of milestones
            total_tasks: Total number of tasks
        """
        logger.info(
            f"🚀 Emitting masterplan_parsing_complete WebSocket event",
            extra={"session_id": session_id, "total_phases": total_phases, "total_tasks": total_tasks}
        )
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_parsing_complete",
            data={
                "session_id": session_id,
                "total_phases": total_phases,
                "total_milestones": total_milestones,
                "total_tasks": total_tasks
            }
        )

    async def emit_masterplan_validation_start(self, session_id: str):
        """
        Emit MasterPlan validation start event.

        Args:
            session_id: Session ID
        """
        logger.info(
            f"🚀 Emitting masterplan_validation_start WebSocket event",
            extra={"session_id": session_id}
        )
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_validation_start",
            data={"session_id": session_id}
        )

    async def emit_masterplan_saving_start(
        self,
        session_id: str,
        total_entities: int
    ):
        """
        Emit MasterPlan saving start event.

        Args:
            session_id: Session ID
            total_entities: Total entities to save (phases + milestones + tasks)
        """
        logger.info(
            f"🚀 Emitting masterplan_saving_start WebSocket event",
            extra={"session_id": session_id, "total_entities": total_entities}
        )
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_saving_start",
            data={
                "session_id": session_id,
                "total_entities": total_entities
            }
        )

    async def emit_masterplan_generation_complete(
        self,
        session_id: str,
        masterplan_id: str,
        project_name: str,
        total_phases: int,
        total_milestones: int,
        total_tasks: int,
        generation_cost_usd: float,
        duration_seconds: float,
        estimated_total_cost_usd: float,
        estimated_duration_minutes: int,
        llm_model: Optional[str] = None,
        workspace_path: Optional[str] = None,
        tech_stack: Optional[Dict[str, Any]] = None,
        architecture_style: Optional[str] = None
    ):
        """
        Emit MasterPlan generation complete event.

        Args:
            session_id: Session ID
            masterplan_id: Generated MasterPlan ID
            project_name: Project name
            total_phases: Total phases
            total_milestones: Total milestones
            total_tasks: Total tasks
            generation_cost_usd: Generation cost in USD
            duration_seconds: Actual generation duration
            estimated_total_cost_usd: Estimated total project cost
            estimated_duration_minutes: Estimated total project duration (in minutes)
            llm_model: LLM model used for generation (optional)
            workspace_path: Workspace path for execution (optional)
            tech_stack: Technology stack info (optional)
            architecture_style: Architecture style (optional)
        """
        # Normalize all durations to seconds for consistency
        estimated_duration_seconds = estimated_duration_minutes * 60

        data = {
            "session_id": session_id,
            "masterplan_id": masterplan_id,
            "project_name": project_name,
            "total_phases": total_phases,
            "total_milestones": total_milestones,
            "total_tasks": total_tasks,
            "generation_cost_usd": generation_cost_usd,
            "duration_seconds": duration_seconds,
            "estimated_total_cost_usd": estimated_total_cost_usd,
            "estimated_duration_seconds": estimated_duration_seconds
        }

        # Add optional fields if provided
        if llm_model:
            data["llm_model"] = llm_model
        if workspace_path:
            data["workspace_path"] = workspace_path
        if tech_stack:
            data["tech_stack"] = tech_stack
        if architecture_style:
            data["architecture_style"] = architecture_style

        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_generation_complete",
            data=data
        )

    # =========================================================================
    # Discovery Generation Progress Events
    # =========================================================================

    async def emit_discovery_generation_start(
        self,
        session_id: str,
        estimated_tokens: int = 8000,
        estimated_duration_seconds: int = 30,
        estimated_cost_usd: float = 0.09
    ):
        """
        Emit Discovery generation start event.

        Args:
            session_id: Session ID
            estimated_tokens: Estimated total tokens (~8000)
            estimated_duration_seconds: Estimated duration in seconds (~30)
            estimated_cost_usd: Estimated cost in USD (~0.09 for Sonnet 4.5)
        """
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_generation_start",
            data={
                "session_id": session_id,
                "estimated_tokens": estimated_tokens,
                "estimated_duration_seconds": estimated_duration_seconds,
                "estimated_cost_usd": estimated_cost_usd
            }
        )

    async def emit_discovery_tokens_progress(
        self,
        session_id: str,
        tokens_received: int,
        estimated_total: int,
        current_phase: str
    ):
        """
        Emit Discovery token progress event.

        Args:
            session_id: Session ID
            tokens_received: Tokens received so far
            estimated_total: Estimated total tokens
            current_phase: Current phase description
        """
        # Conservative percentage (cap at 95%)
        raw_percentage = int((tokens_received / estimated_total) * 100) if estimated_total > 0 else 0
        percentage = min(raw_percentage, 95)

        await self.emit_to_session(
            session_id=session_id,
            event="discovery_tokens_progress",
            data={
                "session_id": session_id,
                "tokens_received": tokens_received,
                "estimated_total": estimated_total,
                "percentage": percentage,
                "current_phase": current_phase
            }
        )

    async def emit_discovery_entity_discovered(
        self,
        session_id: str,
        entity_type: str,  # "bounded_context", "aggregate", "entity", "value_object", "domain_event"
        count: int,
        name: Optional[str] = None
    ):
        """
        Emit Discovery entity discovered event.

        Args:
            session_id: Session ID
            entity_type: Type of entity ("bounded_context", "aggregate", "entity", etc.)
            count: Total count of this entity type discovered so far
            name: Name of the entity (optional)
        """
        data = {
            "session_id": session_id,
            "type": entity_type,
            "count": count
        }

        if name:
            data["name"] = name

        await self.emit_to_session(
            session_id=session_id,
            event="discovery_entity_discovered",
            data=data
        )

    async def emit_discovery_parsing_complete(
        self,
        session_id: str,
        domain: str,
        total_bounded_contexts: int,
        total_aggregates: int,
        total_entities: int
    ):
        """
        Emit Discovery parsing complete event.

        Args:
            session_id: Session ID
            domain: Domain name
            total_bounded_contexts: Total number of bounded contexts
            total_aggregates: Total number of aggregates
            total_entities: Total number of entities
        """
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_parsing_complete",
            data={
                "session_id": session_id,
                "domain": domain,
                "total_bounded_contexts": total_bounded_contexts,
                "total_aggregates": total_aggregates,
                "total_entities": total_entities
            }
        )

    async def emit_discovery_validation_start(self, session_id: str):
        """
        Emit Discovery validation start event.

        Args:
            session_id: Session ID
        """
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_validation_start",
            data={"session_id": session_id}
        )

    async def emit_discovery_saving_start(
        self,
        session_id: str,
        total_entities: int
    ):
        """
        Emit Discovery saving start event.

        Args:
            session_id: Session ID
            total_entities: Total entities to save
        """
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_saving_start",
            data={
                "session_id": session_id,
                "total_entities": total_entities
            }
        )

    async def emit_discovery_generation_complete(
        self,
        session_id: str,
        discovery_id: str,
        domain: str,
        total_bounded_contexts: int,
        total_aggregates: int,
        total_entities: int,
        generation_cost_usd: float,
        duration_seconds: float
    ):
        """
        Emit Discovery generation complete event.

        Args:
            session_id: Session ID
            discovery_id: Generated Discovery ID
            domain: Domain name
            total_bounded_contexts: Total bounded contexts
            total_aggregates: Total aggregates
            total_entities: Total entities
            generation_cost_usd: Generation cost in USD
            duration_seconds: Actual generation duration
        """
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_generation_complete",
            data={
                "session_id": session_id,
                "discovery_id": discovery_id,
                "domain": domain,
                "total_bounded_contexts": total_bounded_contexts,
                "total_aggregates": total_aggregates,
                "total_entities": total_entities,
                "generation_cost_usd": generation_cost_usd,
                "duration_seconds": duration_seconds
            }
        )

    async def emit_discovery_entity_streaming(
        self,
        session_id: str,
        entity_type: str,
        name: str,
        properties: dict,
        chunk_index: int,
        timestamp: float = None
    ):
        """Emit DDD entity discovered during streaming."""
        import time
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_entity_streaming",
            data={
                "session_id": session_id,
                "entity_type": entity_type,  # bounded_context, aggregate, value_object, etc.
                "name": name,
                "properties": properties,
                "chunk_index": chunk_index,
                "timestamp": timestamp or time.time()
            }
        )

    async def emit_discovery_relationship_found(
        self,
        session_id: str,
        from_entity: str,
        to_entity: str,
        relationship_type: str,
        details: dict = None
    ):
        """Emit relationship found between DDD entities."""
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_relationship_found",
            data={
                "session_id": session_id,
                "from_entity": from_entity,
                "to_entity": to_entity,
                "relationship_type": relationship_type,  # publishes_event, depends_on, etc.
                "details": details or {}
            }
        )

    async def emit_discovery_pattern_detected(
        self,
        session_id: str,
        pattern: str,
        confidence: float,
        affected_entities: list,
        description: str = None
    ):
        """Emit architectural pattern detected in discovery."""
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_pattern_detected",
            data={
                "session_id": session_id,
                "pattern": pattern,  # event_sourcing, saga, cqrs, etc.
                "confidence": confidence,
                "affected_entities": affected_entities,
                "description": description or ""
            }
        )

    async def emit_masterplan_phase_progress(
        self,
        session_id: str,
        phase: str,
        progress: dict,
        current_operation: str = None
    ):
        """Emit progress for real MasterPlan processing phase."""
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_phase_progress",
            data={
                "session_id": session_id,
                "phase": phase,  # complexity_analysis, dependency_calculation, etc.
                "progress": progress,  # {analyzed: 10, total: 20, ...}
                "current_operation": current_operation or ""
            }
        )

    async def emit_streaming_progress(
        self,
        session_id: str,
        tokens_received: int,
        estimated_total: int,
        content_preview: str = None,
        entities_found: int = 0
    ):
        """Emit real-time streaming progress with chunk data."""
        import time
        percentage = min(100, int((tokens_received / max(1, estimated_total)) * 100))
        await self.emit_to_session(
            session_id=session_id,
            event="streaming_progress",
            data={
                "session_id": session_id,
                "tokens_received": tokens_received,
                "estimated_total": estimated_total,
                "percentage": percentage,
                "content_preview": content_preview[:100] if content_preview else "",
                "entities_found": entities_found,
                "timestamp": time.time()
            }
        )

    def emit_streaming_progress_sync(
        self,
        session_id: str,
        tokens_received: int,
        estimated_total: int,
        content_preview: str = None,
        entities_found: int = 0
    ):
        """Emit real-time streaming progress SYNCHRONOUSLY (for use in sync contexts)."""
        import time
        import asyncio

        percentage = min(100, int((tokens_received / max(1, estimated_total)) * 100))
        try:
            # Prepare event data
            event_data = {
                "session_id": session_id,
                "tokens_received": tokens_received,
                "estimated_total": estimated_total,
                "percentage": percentage,
                "content_preview": content_preview[:100] if content_preview else "",
                "entities_found": entities_found,
                "timestamp": time.time()
            }

            # CRITICAL: Store event for catch-up BEFORE emitting
            # This ensures late-joining clients can recover this event via request_catch_up
            self.store_event(session_id, "discovery_tokens_progress", event_data)

            # Use stored event loop if available, otherwise try to get current loop
            loop = self.event_loop
            if not loop:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.get_event_loop()

            if not loop or not loop.is_running():
                logger.info(f"⚠️ No running event loop, skipping emit for {session_id}")
                return

            # Use run_coroutine_threadsafe to execute from sync context
            future = asyncio.run_coroutine_threadsafe(
                self.sio.emit(
                    "discovery_tokens_progress",
                    event_data,
                    room=session_id
                ),
                loop
            )
            logger.info(f"✅ Queued discovery_tokens_progress to {session_id}: {tokens_received}/{estimated_total} ({percentage}%)")
        except RuntimeError as e:
            # Event loop might not exist, try fallback
            if "There is no current event loop" in str(e) or "no running event loop" in str(e):
                logger.info(f"⚠️ No event loop available, skipping emit: {e}")
            else:
                logger.error(f"Error emitting streaming progress sync: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error emitting streaming progress sync: {e}", exc_info=True)

    # =========================================================================
    # MGE V2 Execution Progress Events (Opción 2)
    # =========================================================================

    async def emit_execution_started(
        self,
        session_id: str,
        execution_id: str,
        total_tasks: int,
        phases: list
    ):
        """
        Emit execution started event.

        Args:
            session_id: Session ID
            execution_id: Execution ID (masterplan_id)
            total_tasks: Total number of tasks to execute
            phases: List of phase objects with structure:
                    [{"phase": 1, "name": "Discovery", "task_count": 5, "status": "pending"}, ...]
        """
        from datetime import datetime, timezone

        await self.emit_to_session(
            session_id=session_id,
            event="execution_started",
            data={
                "type": "execution_started",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "data": {
                    "execution_id": execution_id,
                    "total_tasks": total_tasks,
                    "phases": phases
                }
            }
        )
        logger.info(
            f"✅ Emitted execution_started for {execution_id}: {total_tasks} tasks across {len(phases)} phases"
        )

    async def emit_progress_update(
        self,
        session_id: str,
        task_id: str,
        task_name: str,
        phase: int,
        phase_name: str,
        status: str,
        progress: int,
        progress_percent: float,
        completed_tasks: int,
        total_tasks: int,
        current_wave: int,
        duration_ms: float,
        subtask_status: dict = None
    ):
        """
        Emit progress update event (main event - 120 total).

        Args:
            session_id: Session ID
            task_id: Task ID (e.g., "task_001")
            task_name: Task name
            phase: Phase number (0-4)
            phase_name: Phase name (Discovery, Analysis, Planning, Execution, Validation)
            status: Task status (pending, in_progress, completed, failed)
            progress: Number of completed tasks
            progress_percent: Progress percentage (0-100)
            completed_tasks: Number of completed tasks
            total_tasks: Total number of tasks
            current_wave: Current execution wave number
            duration_ms: Task duration in milliseconds
            subtask_status: Optional subtask status dict
        """
        from datetime import datetime, timezone

        data = {
            "type": "progress_update",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "data": {
                "task_id": task_id,
                "task_name": task_name,
                "phase": phase,
                "phase_name": phase_name,
                "status": status,
                "progress": progress,
                "progress_percent": round(progress_percent, 2),
                "completed_tasks": completed_tasks,
                "total_tasks": total_tasks,
                "current_wave": current_wave,
                "duration_ms": round(duration_ms, 2)
            }
        }

        if subtask_status:
            data["data"]["subtask_status"] = subtask_status

        await self.emit_to_session(
            session_id=session_id,
            event="progress_update",
            data=data
        )
        logger.debug(
            f"📊 Progress: {task_id} ({status}) - {progress_percent:.1f}% ({completed_tasks}/{total_tasks})"
        )

    async def emit_artifact_created(
        self,
        session_id: str,
        artifact_id: str,
        artifact_name: str,
        artifact_type: str,
        file_path: str,
        size_bytes: int,
        task_id: str = None,
        metadata: dict = None
    ):
        """
        Emit artifact created event (~45 events total).

        Args:
            session_id: Session ID
            artifact_id: Artifact ID (UUID)
            artifact_name: Artifact name (e.g., "auth.py")
            artifact_type: Artifact type (file, directory, config, test, etc.)
            file_path: Relative file path
            size_bytes: File size in bytes
            task_id: Associated task ID (optional)
            metadata: Additional metadata (optional)
        """
        from datetime import datetime, timezone

        data = {
            "type": "artifact_created",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "data": {
                "artifact_id": artifact_id,
                "artifact_name": artifact_name,
                "artifact_type": artifact_type,
                "file_path": file_path,
                "size_bytes": size_bytes
            }
        }

        if task_id:
            data["data"]["task_id"] = task_id
        if metadata:
            data["data"]["metadata"] = metadata

        await self.emit_to_session(
            session_id=session_id,
            event="artifact_created",
            data=data
        )
        logger.info(
            f"📦 Artifact created: {artifact_name} ({artifact_type}) - {size_bytes} bytes"
        )

    async def emit_wave_completed(
        self,
        session_id: str,
        wave_number: int,
        tasks_in_wave: int,
        successful_tasks: int,
        failed_tasks: int,
        duration_ms: float,
        artifacts_created: int
    ):
        """
        Emit wave completed event (8-10 events total).

        Args:
            session_id: Session ID
            wave_number: Wave number
            tasks_in_wave: Number of tasks in this wave
            successful_tasks: Number of successful tasks
            failed_tasks: Number of failed tasks
            duration_ms: Wave duration in milliseconds
            artifacts_created: Number of artifacts created in this wave
        """
        from datetime import datetime, timezone

        await self.emit_to_session(
            session_id=session_id,
            event="wave_completed",
            data={
                "type": "wave_completed",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "data": {
                    "wave_number": wave_number,
                    "tasks_in_wave": tasks_in_wave,
                    "successful_tasks": successful_tasks,
                    "failed_tasks": failed_tasks,
                    "duration_ms": round(duration_ms, 2),
                    "artifacts_created": artifacts_created
                }
            }
        )
        logger.info(
            f"🌊 Wave {wave_number} completed: {successful_tasks}/{tasks_in_wave} tasks successful, "
            f"{artifacts_created} artifacts created"
        )

    async def emit_error(
        self,
        session_id: str,
        error_id: str,
        task_id: str,
        task_name: str,
        error_type: str,
        error_message: str,
        stack_trace: str = None,
        retry_count: int = 0,
        max_retries: int = 3,
        recoverable: bool = True
    ):
        """
        Emit error event (0-20 events total, only on failures).

        Args:
            session_id: Session ID
            error_id: Error ID (UUID)
            task_id: Task ID where error occurred
            task_name: Task name
            error_type: Error type (validation_error, generation_error, etc.)
            error_message: Error message
            stack_trace: Stack trace (optional)
            retry_count: Current retry count
            max_retries: Maximum retry attempts
            recoverable: Whether error is recoverable
        """
        from datetime import datetime, timezone

        data = {
            "type": "error",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "data": {
                "error_id": error_id,
                "task_id": task_id,
                "task_name": task_name,
                "error_type": error_type,
                "error_message": error_message,
                "retry_count": retry_count,
                "max_retries": max_retries,
                "recoverable": recoverable
            }
        }

        if stack_trace:
            data["data"]["stack_trace"] = stack_trace

        await self.emit_to_session(
            session_id=session_id,
            event="error",
            data=data
        )
        logger.error(
            f"❌ Error in {task_id}: {error_message} (retry {retry_count}/{max_retries})"
        )

    async def emit_execution_completed(
        self,
        session_id: str,
        execution_id: str,
        status: str,
        total_tasks: int,
        completed_tasks: int,
        failed_tasks: int,
        skipped_tasks: int,
        total_duration_ms: float,
        artifacts_created: int,
        final_stats: dict = None
    ):
        """
        Emit execution completed event (1 event at end).

        Args:
            session_id: Session ID
            execution_id: Execution ID (masterplan_id)
            status: Final status (completed, failed, partial_success)
            total_tasks: Total number of tasks
            completed_tasks: Number of completed tasks
            failed_tasks: Number of failed tasks
            skipped_tasks: Number of skipped tasks
            total_duration_ms: Total execution duration in milliseconds
            artifacts_created: Total artifacts created
            final_stats: Additional final statistics (optional)
        """
        from datetime import datetime, timezone

        data = {
            "type": "execution_completed",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "data": {
                "execution_id": execution_id,
                "status": status,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "skipped_tasks": skipped_tasks,
                "total_duration_ms": round(total_duration_ms, 2),
                "artifacts_created": artifacts_created
            }
        }

        if final_stats:
            data["data"]["final_stats"] = final_stats

        await self.emit_to_session(
            session_id=session_id,
            event="execution_completed",
            data=data
        )
        logger.info(
            f"🎉 Execution {execution_id} completed: {status} - "
            f"{completed_tasks}/{total_tasks} tasks successful, {artifacts_created} artifacts created"
        )
