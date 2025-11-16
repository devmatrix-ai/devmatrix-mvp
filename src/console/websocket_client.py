"""WebSocket client for real-time pipeline updates."""

import asyncio
import json
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from src.observability import get_logger
import socketio

logger = get_logger(__name__)


@dataclass
class PipelineUpdate:
    """Pipeline execution update from WebSocket."""

    type: str  # progress_update, artifact_created, test_result, error, log_message
    timestamp: str
    data: Dict[str, Any]


class WebSocketClient:
    """Manages WebSocket connection to DevMatrix backend."""

    def __init__(self, url: str, session_id: str):
        """Initialize WebSocket client.

        Args:
            url: WebSocket server URL
            session_id: Session ID for connection
        """
        self.url = url
        self.session_id = session_id
        self.sio = socketio.Client(reconnection=True, reconnection_delay=1)
        self.connected = False
        self.callbacks: Dict[str, list[Callable]] = {}
        self._setup_handlers()
        logger.info(f"WebSocketClient initialized for session: {session_id}")

    def _setup_handlers(self) -> None:
        """Setup Socket.IO event handlers."""

        @self.sio.event
        def connect():
            """Handle connection established."""
            self.connected = True
            logger.info("WebSocket connected")
            self._emit_callback("connected")

        @self.sio.on("pipeline_update")
        def on_pipeline_update(data: Dict[str, Any]):
            """Handle pipeline progress update."""
            update = PipelineUpdate(
                type="progress_update", timestamp=data.get("timestamp"), data=data
            )
            self._emit_callback("pipeline_update", update)

        @self.sio.on("artifact_created")
        def on_artifact_created(data: Dict[str, Any]):
            """Handle artifact creation notification."""
            update = PipelineUpdate(
                type="artifact_created", timestamp=data.get("timestamp"), data=data
            )
            self._emit_callback("artifact_created", update)

        @self.sio.on("test_result")
        def on_test_result(data: Dict[str, Any]):
            """Handle test execution result."""
            update = PipelineUpdate(
                type="test_result", timestamp=data.get("timestamp"), data=data
            )
            self._emit_callback("test_result", update)

        @self.sio.on("error")
        def on_error(data: Dict[str, Any]):
            """Handle error notification."""
            update = PipelineUpdate(
                type="error", timestamp=data.get("timestamp"), data=data
            )
            self._emit_callback("error", update)

        @self.sio.on("log_message")
        def on_log_message(data: Dict[str, Any]):
            """Handle log message."""
            update = PipelineUpdate(
                type="log_message", timestamp=data.get("timestamp"), data=data
            )
            self._emit_callback("log_message", update)

        @self.sio.event
        def disconnect():
            """Handle disconnection."""
            self.connected = False
            logger.warning("WebSocket disconnected")
            self._emit_callback("disconnected")

    def connect(self, timeout: int = 10) -> bool:
        """Connect to WebSocket server.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully
        """
        try:
            self.sio.connect(
                self.url,
                auth={"session_id": self.session_id},
                transports=["websocket", "polling"],
                wait_timeout=timeout,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from server."""
        if self.connected:
            self.sio.disconnect()
            logger.info("WebSocket disconnected")

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to an event.

        Args:
            event: Event name (pipeline_update, artifact_created, test_result, error, log_message)
            callback: Callback function to invoke when event occurs
        """
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
        logger.debug(f"Subscribed to event: {event}")

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Unsubscribe from an event.

        Args:
            event: Event name
            callback: Callback to remove
        """
        if event in self.callbacks:
            self.callbacks[event] = [cb for cb in self.callbacks[event] if cb != callback]
            logger.debug(f"Unsubscribed from event: {event}")

    def send_command(self, command: str, args: Optional[Dict[str, Any]] = None) -> None:
        """Send command to backend.

        Args:
            command: Command name
            args: Command arguments
        """
        if not self.connected:
            logger.warning("Cannot send command: not connected")
            return

        try:
            self.sio.emit("execute_command", {"command": command, "args": args or {}})
            logger.debug(f"Command sent: {command}")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    def request_pipeline_state(self) -> None:
        """Request current pipeline state."""
        if not self.connected:
            logger.warning("Cannot request state: not connected")
            return

        try:
            self.sio.emit("get_pipeline_state")
            logger.debug("Pipeline state requested")
        except Exception as e:
            logger.error(f"Failed to request state: {e}")

    def _emit_callback(self, event: str, data: Optional[Any] = None) -> None:
        """Internal callback emitter.

        Args:
            event: Event name
            data: Event data
        """
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    if data:
                        callback(data)
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Callback error for {event}: {e}")


class WebSocketPool:
    """Manages multiple WebSocket connections for different sessions."""

    def __init__(self, base_url: str):
        """Initialize WebSocket pool.

        Args:
            base_url: Base WebSocket URL (e.g., ws://localhost:8000/ws)
        """
        self.base_url = base_url
        self.clients: Dict[str, WebSocketClient] = {}
        logger.info("WebSocketPool initialized")

    def get_client(self, session_id: str) -> WebSocketClient:
        """Get or create client for session.

        Args:
            session_id: Session ID

        Returns:
            WebSocketClient instance
        """
        if session_id not in self.clients:
            self.clients[session_id] = WebSocketClient(self.base_url, session_id)
        return self.clients[session_id]

    def connect_all(self, timeout: int = 10) -> int:
        """Connect all clients.

        Args:
            timeout: Connection timeout

        Returns:
            Number of successful connections
        """
        connected = 0
        for session_id, client in self.clients.items():
            if client.connect(timeout):
                connected += 1
        return connected

    def disconnect_all(self) -> None:
        """Disconnect all clients."""
        for client in self.clients.values():
            client.disconnect()
        logger.info("All clients disconnected")
