"""
WebSocket Router

Real-time communication endpoints for chat, executions, masterplans, and workspace updates.
"""

import asyncio
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import socketio
import jwt

from src.services.chat_service import ChatService
from src.services.workspace_service import WorkspaceService
from src.observability import StructuredLogger
from src.observability.global_metrics import metrics_collector
from src.websocket import WebSocketManager
from src.config.settings import get_settings


router = APIRouter()
logger = StructuredLogger("websocket")
# Use global metrics collector
metrics = metrics_collector
settings = get_settings()


# ==========================================
# JWT Validation for WebSocket
# ==========================================

def validate_jwt_token(token: str) -> Optional[Dict]:
    """
    Validate JWT token and extract user info.

    Args:
        token: JWT access token (can include 'Bearer ' prefix)

    Returns:
        Dict with user_id and other claims, or None if invalid
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Decode token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None

# Socket.IO server with robust timeout configuration
# These settings prevent disconnections during long-running operations (e.g., masterplan generation)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True,
    # Increase intervals to handle long-running operations
    ping_timeout=120,  # Wait 120s for ping response before disconnecting (2x ping_interval)
    ping_interval=60,  # Send ping every 60s to keep connection alive
    max_http_buffer_size=10_000_000,  # 10MB buffer for large messages
    # Enable compression for large payloads
    compression_threshold=1024,  # Compress payloads > 1KB
    # Allow longer timeouts for slow clients
    http_compression=True,
)

# WebSocket Manager (global instance)
ws_manager = WebSocketManager(sio)

# Services - use global metrics collector for LLM metrics
chat_service = ChatService(metrics_collector=metrics, websocket_manager=ws_manager)
workspace_service = WorkspaceService()

# Active connections tracking
active_connections: Dict[str, Set[str]] = {
    "chat": set(),
    "executions": set(),
    "masterplans": set(),
}


# ==========================================
# Socket.IO Event Handlers
# ==========================================

@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")

    # Metrics
    metrics.increment_counter(
        "websocket_connections_total",
        labels={"type": "connect"},
        help_text="Total WebSocket connections"
    )
    current_active = len(active_connections['chat']) + len(active_connections['executions']) + len(active_connections['masterplans'])
    metrics.set_gauge(
        "websocket_connections_active",
        current_active + 1,
        help_text="Active WebSocket connections"
    )

    await sio.emit('connected', {'sid': sid}, room=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")

    # Remove from all rooms
    for room_set in active_connections.values():
        room_set.discard(sid)

    # Metrics
    metrics.increment_counter(
        "websocket_connections_total",
        labels={"type": "disconnect"},
        help_text="Total WebSocket disconnections"
    )
    current_active = len(active_connections['chat']) + len(active_connections['executions']) + len(active_connections['masterplans'])
    metrics.set_gauge(
        "websocket_connections_active",
        current_active,
        help_text="Active WebSocket connections"
    )


# ==========================================
# Chat Events
# ==========================================

@sio.event
async def join_chat(sid, data):
    """
    Join chat room.

    Expected data:
        {
            "conversation_id": "optional-existing-conversation-id",
            "workspace_id": "optional-workspace-id",
            "token": "JWT access token"  # Required for authentication
        }
    """
    try:
        # Extract authentication token
        token = data.get('token')
        if not token:
            await sio.emit('error', {'message': 'Authentication token required'}, room=sid)
            logger.warning(f"Client {sid} joined without token")
            return

        # Validate JWT token and extract user info
        payload = validate_jwt_token(token)
        if not payload:
            await sio.emit('error', {'message': 'Invalid or expired token'}, room=sid)
            logger.warning(f"Client {sid} joined with invalid token")
            return

        # Extract user_id from JWT payload
        user_id = payload.get('sub')  # 'sub' contains user_id in our JWT
        if not user_id:
            await sio.emit('error', {'message': 'Invalid token format'}, room=sid)
            logger.warning(f"Client {sid} token missing user_id")
            return

        conversation_id = data.get('conversation_id')
        workspace_id = data.get('workspace_id')

        # Create or get conversation
        if conversation_id:
            conversation = chat_service.get_conversation(conversation_id)
            if not conversation:
                # Conversation not found (e.g., after server restart)
                # Create a new one and notify client of the new ID
                logger.info(f"Conversation {conversation_id} not found, creating new one")
                conversation_id = chat_service.create_conversation(
                    workspace_id=workspace_id,
                    metadata={'sid': sid, 'recreated': True},
                    session_id=sid,
                    user_id=user_id  # Use authenticated user_id
                )
                conversation = chat_service.get_conversation(conversation_id)
            else:
                # Update metadata with current SID (important for reconnections)
                # This ensures Discovery/MasterPlan events reach the correct client
                conversation.metadata['sid'] = sid
                chat_service.update_conversation_metadata(conversation_id, conversation.metadata)
        else:
            conversation_id = chat_service.create_conversation(
                workspace_id=workspace_id,
                metadata={'sid': sid},
                session_id=sid,
                user_id=user_id  # Use authenticated user_id
            )
            conversation = chat_service.get_conversation(conversation_id)

        # Join room
        await sio.enter_room(sid, f"chat_{conversation_id}")
        active_connections['chat'].add(sid)

        # Send conversation history
        history = conversation.get_history()

        await sio.emit('chat_joined', {
            'conversation_id': conversation_id,
            'workspace_id': conversation.workspace_id,
            'message_count': len(history),
            'history': history,
            'user_id': user_id,
        }, room=sid)

        logger.info(f"Client {sid} (user {user_id}) joined chat {conversation_id}")

    except Exception as e:
        logger.error(f"Error joining chat: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def send_message(sid, data):
    """
    Send chat message.

    Expected data:
        {
            "conversation_id": "conversation-id",
            "content": "message content",
            "metadata": {}  # optional
        }
    """
    import time
    start_time = time.time()

    try:
        conversation_id = data.get('conversation_id')
        content = data.get('content')
        metadata = data.get('metadata', {})

        if not conversation_id or not content:
            await sio.emit('error', {
                'message': 'conversation_id and content are required'
            }, room=sid)
            metrics.increment_counter(
                "websocket_errors_total",
                labels={"event": "send_message", "error_type": "validation"},
                help_text="Total WebSocket errors"
            )
            return

        # Metrics: Message received
        metrics.increment_counter(
            "websocket_messages_total",
            labels={"event": "send_message", "direction": "received"},
            help_text="Total WebSocket messages"
        )

        # Echo user message immediately
        await sio.emit('message', {
            'type': 'user_message',
            'content': content,
            'timestamp': None,  # Will be set by frontend
        }, room=f"chat_{conversation_id}")

        # Process message and stream response
        chunk_count = 0
        async for chunk in chat_service.send_message(
            conversation_id=conversation_id,
            content=content,
            metadata=metadata,
        ):
            await sio.emit('message', chunk, room=f"chat_{conversation_id}")
            chunk_count += 1

        # Metrics: Response sent
        metrics.increment_counter(
            "websocket_messages_total",
            value=chunk_count,
            labels={"event": "send_message", "direction": "sent"},
            help_text="Total WebSocket messages"
        )

        # Metrics: Message duration
        duration = time.time() - start_time
        metrics.observe_histogram(
            "websocket_message_duration_seconds",
            duration,
            labels={"event": "send_message"},
            help_text="WebSocket message processing duration"
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)
        metrics.increment_counter(
            "websocket_errors_total",
            labels={"event": "send_message", "error_type": "processing"},
            help_text="Total WebSocket errors"
        )


@sio.event
async def leave_chat(sid, data):
    """Leave chat room."""
    try:
        conversation_id = data.get('conversation_id')
        if conversation_id:
            await sio.leave_room(sid, f"chat_{conversation_id}")
            active_connections['chat'].discard(sid)
            logger.info(f"Client {sid} left chat {conversation_id}")
    except Exception as e:
        logger.error(f"Error leaving chat: {e}")


# ==========================================
# Workspace Events
# ==========================================

@sio.event
async def get_file_tree(sid, data):
    """
    Get workspace file tree.

    Expected data:
        {
            "workspace_id": "workspace-id"
        }
    """
    try:
        workspace_id = data.get('workspace_id')
        if not workspace_id:
            await sio.emit('error', {
                'message': 'workspace_id is required'
            }, room=sid)
            return

        file_tree = workspace_service.get_file_tree(workspace_id)
        if file_tree:
            await sio.emit('file_tree', {
                'workspace_id': workspace_id,
                'tree': file_tree.to_dict(),
            }, room=sid)
        else:
            await sio.emit('error', {
                'message': f'Workspace {workspace_id} not found'
            }, room=sid)

    except Exception as e:
        logger.error(f"Error getting file tree: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def read_file(sid, data):
    """
    Read file content.

    Expected data:
        {
            "workspace_id": "workspace-id",
            "file_path": "relative/path/to/file.py"
        }
    """
    try:
        workspace_id = data.get('workspace_id')
        file_path = data.get('file_path')

        if not workspace_id or not file_path:
            await sio.emit('error', {
                'message': 'workspace_id and file_path are required'
            }, room=sid)
            return

        content = await workspace_service.read_file(workspace_id, file_path)

        if content is not None:
            await sio.emit('file_content', {
                'workspace_id': workspace_id,
                'file_path': file_path,
                'content': content,
            }, room=sid)
        else:
            await sio.emit('error', {
                'message': f'File {file_path} not found'
            }, room=sid)

    except Exception as e:
        logger.error(f"Error reading file: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def write_file(sid, data):
    """
    Write file content.

    Expected data:
        {
            "workspace_id": "workspace-id",
            "file_path": "relative/path/to/file.py",
            "content": "file content"
        }
    """
    try:
        workspace_id = data.get('workspace_id')
        file_path = data.get('file_path')
        content = data.get('content')

        if not workspace_id or not file_path or content is None:
            await sio.emit('error', {
                'message': 'workspace_id, file_path, and content are required'
            }, room=sid)
            return

        success = await workspace_service.write_file(
            workspace_id, file_path, content
        )

        if success:
            # Metrics
            metrics.increment_counter(
                "websocket_workspace_operations_total",
                labels={"operation": "write_file", "result": "success"},
                help_text="Total workspace operations"
            )

            await sio.emit('file_written', {
                'workspace_id': workspace_id,
                'file_path': file_path,
                'success': True,
            }, room=sid)

            # Broadcast file tree update to all clients in workspace
            file_tree = workspace_service.get_file_tree(workspace_id)
            if file_tree:
                await sio.emit('file_tree', {
                    'workspace_id': workspace_id,
                    'tree': file_tree.to_dict(),
                }, room=f"workspace_{workspace_id}")
        else:
            metrics.increment_counter(
                "websocket_workspace_operations_total",
                labels={"operation": "write_file", "result": "failure"},
                help_text="Total workspace operations"
            )
            await sio.emit('error', {
                'message': f'Failed to write file {file_path}'
            }, room=sid)

    except Exception as e:
        logger.error(f"Error writing file: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)
        metrics.increment_counter(
            "websocket_errors_total",
            labels={"event": "write_file", "error_type": "processing"},
            help_text="Total WebSocket errors"
        )


# ==========================================
# Execution Events
# ==========================================

@sio.event
async def join_execution(sid, data):
    """
    Join execution monitoring room.

    Expected data:
        {
            "execution_id": "execution-id"
        }
    """
    try:
        execution_id = data.get('execution_id')
        if not execution_id:
            await sio.emit('error', {
                'message': 'execution_id is required'
            }, room=sid)
            return

        await sio.enter_room(sid, f"execution_{execution_id}")
        active_connections['executions'].add(sid)

        await sio.emit('execution_joined', {
            'execution_id': execution_id,
        }, room=sid)

        logger.info(f"Client {sid} joined execution {execution_id}")

    except Exception as e:
        logger.error(f"Error joining execution: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def leave_execution(sid, data):
    """Leave execution monitoring room."""
    try:
        execution_id = data.get('execution_id')
        if execution_id:
            await sio.leave_room(sid, f"execution_{execution_id}")
            active_connections['executions'].discard(sid)
            logger.info(f"Client {sid} left execution {execution_id}")
    except Exception as e:
        logger.error(f"Error leaving execution: {e}")


# ==========================================
# Masterplan Events
# ==========================================

@sio.event
async def join_masterplan(sid, data):
    """
    Join masterplan monitoring room for real-time execution updates.

    Expected data:
        {
            "masterplan_id": "masterplan-uuid"
        }
    """
    try:
        masterplan_id = data.get('masterplan_id')
        if not masterplan_id:
            await sio.emit('error', {
                'message': 'masterplan_id is required'
            }, room=sid)
            return

        # Join masterplan-specific room
        room_name = f"masterplan_{masterplan_id}"
        await sio.enter_room(sid, room_name)
        active_connections['masterplans'].add(sid)

        await sio.emit('masterplan_joined', {
            'masterplan_id': masterplan_id,
            'room': room_name,
        }, room=sid)

        logger.info(f"Client {sid} joined masterplan {masterplan_id}")

        # Metrics
        metrics.increment_counter(
            "websocket_masterplan_connections_total",
            labels={"action": "join"},
            help_text="Total masterplan WebSocket connections"
        )

    except Exception as e:
        logger.error(f"Error joining masterplan: {e}", exc_info=True)
        await sio.emit('error', {'message': str(e)}, room=sid)


@sio.event
async def leave_masterplan(sid, data):
    """Leave masterplan monitoring room."""
    try:
        masterplan_id = data.get('masterplan_id')
        if masterplan_id:
            room_name = f"masterplan_{masterplan_id}"
            await sio.leave_room(sid, room_name)
            active_connections['masterplans'].discard(sid)
            logger.info(f"Client {sid} left masterplan {masterplan_id}")

            # Metrics
            metrics.increment_counter(
                "websocket_masterplan_connections_total",
                labels={"action": "leave"},
                help_text="Total masterplan WebSocket disconnections"
            )
    except Exception as e:
        logger.error(f"Error leaving masterplan: {e}")


# ==========================================
# Utility Functions
# ==========================================

async def broadcast_execution_update(execution_id: str, update: dict):
    """
    Broadcast execution update to all connected clients.

    Args:
        execution_id: Execution ID
        update: Update data
    """
    await sio.emit('execution_update', update, room=f"execution_{execution_id}")


async def broadcast_workspace_update(workspace_id: str, update: dict):
    """
    Broadcast workspace update to all connected clients.

    Args:
        workspace_id: Workspace ID
        update: Update data
    """
    await sio.emit('workspace_update', update, room=f"workspace_{workspace_id}")


async def broadcast_masterplan_update(masterplan_id: str, event_name: str, update: dict):
    """
    Broadcast masterplan execution update to all connected clients.

    Args:
        masterplan_id: Masterplan ID
        event_name: Event name (e.g., 'masterplan_execution_start')
        update: Update data
    """
    await sio.emit(event_name, update, room=f"masterplan_{masterplan_id}")


# ==========================================
# FastAPI WebSocket Endpoint (fallback)
# ==========================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Basic WebSocket endpoint (fallback for simple connections).
    Prefer using Socket.IO for full functionality.
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")


# ==========================================
# Socket.IO ASGI Application
# ==========================================

# Create Socket.IO ASGI app
sio_app = socketio.ASGIApp(
    socketio_server=sio,
    socketio_path='/socket.io',
)
