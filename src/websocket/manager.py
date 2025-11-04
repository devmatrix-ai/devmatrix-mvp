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
        logger.info("WebSocketManager initialized")

    def set_sio_server(self, sio_server: socketio.AsyncServer):
        """
        Set Socket.IO server (used when creating manager before sio is available).

        Args:
            sio_server: Socket.IO server instance
        """
        self.sio = sio_server
        logger.info("Socket.IO server set")

    async def emit_to_session(
        self,
        session_id: str,
        event: str,
        data: Dict[str, Any]
    ):
        """
        Emit event to a specific session (by sid).

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
            await self.sio.emit(event, data, room=session_id)
            logger.info(
                f"✅ Emitted event to session",
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
        Emit event to chat room.

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

    # =========================================================================
    # MasterPlan Generation Progress Events
    # =========================================================================

    async def emit_masterplan_generation_start(
        self,
        session_id: str,
        discovery_id: str,
        estimated_tokens: int = 17000,
        estimated_duration_seconds: int = 90
    ):
        """
        Emit MasterPlan generation start event.

        Args:
            session_id: Session ID
            discovery_id: Discovery document ID
            estimated_tokens: Estimated total tokens (~17000)
            estimated_duration_seconds: Estimated duration in seconds (~90)
        """
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_generation_start",
            data={
                "discovery_id": discovery_id,
                "session_id": session_id,
                "estimated_tokens": estimated_tokens,
                "estimated_duration_seconds": estimated_duration_seconds
            }
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
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_parsing_complete",
            data={
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
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_validation_start",
            data={}
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
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_saving_start",
            data={"total_entities": total_entities}
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
        estimated_duration_minutes: int
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
            estimated_duration_minutes: Estimated total project duration
        """
        await self.emit_to_session(
            session_id=session_id,
            event="masterplan_generation_complete",
            data={
                "masterplan_id": masterplan_id,
                "project_name": project_name,
                "total_phases": total_phases,
                "total_milestones": total_milestones,
                "total_tasks": total_tasks,
                "generation_cost_usd": generation_cost_usd,
                "duration_seconds": duration_seconds,
                "estimated_total_cost_usd": estimated_total_cost_usd,
                "estimated_duration_minutes": estimated_duration_minutes
            }
        )

    # =========================================================================
    # Discovery Generation Progress Events
    # =========================================================================

    async def emit_discovery_generation_start(
        self,
        session_id: str,
        estimated_tokens: int = 8000,
        estimated_duration_seconds: int = 30
    ):
        """
        Emit Discovery generation start event.

        Args:
            session_id: Session ID
            estimated_tokens: Estimated total tokens (~8000)
            estimated_duration_seconds: Estimated duration in seconds (~30)
        """
        await self.emit_to_session(
            session_id=session_id,
            event="discovery_generation_start",
            data={
                "session_id": session_id,
                "estimated_tokens": estimated_tokens,
                "estimated_duration_seconds": estimated_duration_seconds
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
            data={}
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
            data={"total_entities": total_entities}
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
                "discovery_id": discovery_id,
                "domain": domain,
                "total_bounded_contexts": total_bounded_contexts,
                "total_aggregates": total_aggregates,
                "total_entities": total_entities,
                "generation_cost_usd": generation_cost_usd,
                "duration_seconds": duration_seconds
            }
        )
