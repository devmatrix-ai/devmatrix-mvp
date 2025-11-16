"""Integration tests for WebSocket connection with real backend."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.console.websocket_client import WebSocketClient, WebSocketPool
from src.console.config import Config


@pytest.fixture
def config():
    """Test configuration."""
    return Config(
        websocket_url="ws://localhost:8000/socket.io/",
        api_base_url="http://localhost:8000",
    )


@pytest.fixture
def session_id():
    """Test session ID."""
    return "test_session_20251116_abc123"


class TestWebSocketClientIntegration:
    """Integration tests for WebSocket client."""

    def test_client_initialization(self, config, session_id):
        """Test WebSocket client initializes correctly."""
        client = WebSocketClient(config.websocket_url, session_id)

        assert client.url == config.websocket_url
        assert client.session_id == session_id
        assert client.connected is False
        assert len(client.callbacks) == 0

    def test_event_subscription(self, session_id):
        """Test event subscription system."""
        client = WebSocketClient("ws://localhost:8000", session_id)

        callback = MagicMock()
        client.subscribe("pipeline_update", callback)

        assert "pipeline_update" in client.callbacks
        assert callback in client.callbacks["pipeline_update"]

    def test_event_unsubscription(self, session_id):
        """Test event unsubscription."""
        client = WebSocketClient("ws://localhost:8000", session_id)

        callback = MagicMock()
        client.subscribe("pipeline_update", callback)
        client.unsubscribe("pipeline_update", callback)

        assert callback not in client.callbacks["pipeline_update"]

    def test_multiple_subscribers(self, session_id):
        """Test multiple subscribers to same event."""
        client = WebSocketClient("ws://localhost:8000", session_id)

        callback1 = MagicMock()
        callback2 = MagicMock()

        client.subscribe("pipeline_update", callback1)
        client.subscribe("pipeline_update", callback2)

        assert len(client.callbacks["pipeline_update"]) == 2

    def test_emit_callback(self, session_id):
        """Test callback emission."""
        client = WebSocketClient("ws://localhost:8000", session_id)

        callback = MagicMock()
        client.subscribe("test_event", callback)

        # Simulate callback emission
        client._emit_callback("test_event", {"data": "test"})

        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure_handling(self, session_id):
        """Test graceful handling of connection failures."""
        client = WebSocketClient("ws://localhost:9999", session_id)  # Wrong port

        # Should not raise, just return False
        result = client.connect(timeout=1)
        assert result is False
        assert client.connected is False

    def test_websocket_pool_creation(self, config):
        """Test WebSocket pool management."""
        pool = WebSocketPool(config.websocket_url)

        client1 = pool.get_client("session_1")
        client2 = pool.get_client("session_2")
        client1_again = pool.get_client("session_1")

        assert client1 == client1_again
        assert client1 != client2
        assert "session_1" in pool.clients
        assert "session_2" in pool.clients

    def test_websocket_pool_disconnect(self, config):
        """Test disconnecting all clients."""
        pool = WebSocketPool(config.websocket_url)

        pool.get_client("session_1")
        pool.get_client("session_2")

        # Should not raise
        pool.disconnect_all()

        # All clients should be marked disconnected
        for client in pool.clients.values():
            assert client.connected is False


class TestWebSocketEventFlow:
    """Test realistic event flows."""

    def test_pipeline_update_event(self, session_id):
        """Test handling pipeline update event."""
        from src.console.websocket_client import PipelineUpdate

        client = WebSocketClient("ws://localhost:8000", session_id)
        callback = MagicMock()

        client.subscribe("pipeline_update", callback)

        # Simulate backend sending update
        update_data = {
            "type": "progress_update",
            "timestamp": "2025-11-16T14:30:00",
            "current_task": "Running tests",
            "progress": 65,
            "total_tasks": 10,
            "completed_tasks": 6,
        }

        update = PipelineUpdate(
            type="progress_update",
            timestamp=update_data["timestamp"],
            data=update_data,
        )

        client._emit_callback("pipeline_update", update)

        callback.assert_called_once_with(update)
        assert callback.call_args[0][0].data["progress"] == 65

    def test_artifact_created_event(self, session_id):
        """Test artifact creation notification."""
        from src.console.websocket_client import PipelineUpdate

        client = WebSocketClient("ws://localhost:8000", session_id)
        callback = MagicMock()

        client.subscribe("artifact_created", callback)

        artifact_data = {
            "type": "file",
            "path": "/workspace/auth.py",
            "size": 1024,
            "timestamp": "2025-11-16T14:30:15",
        }

        update = PipelineUpdate(
            type="artifact_created",
            timestamp=artifact_data["timestamp"],
            data=artifact_data,
        )

        client._emit_callback("artifact_created", update)

        callback.assert_called_once()
        assert callback.call_args[0][0].data["path"] == "/workspace/auth.py"

    def test_error_event(self, session_id):
        """Test error notification handling."""
        from src.console.websocket_client import PipelineUpdate

        client = WebSocketClient("ws://localhost:8000", session_id)
        callback = MagicMock()

        client.subscribe("error", callback)

        error_data = {
            "message": "Test execution failed",
            "error_type": "AssertionError",
            "timestamp": "2025-11-16T14:30:30",
        }

        update = PipelineUpdate(
            type="error", timestamp=error_data["timestamp"], data=error_data
        )

        client._emit_callback("error", update)

        callback.assert_called_once()
        assert "Test execution failed" in callback.call_args[0][0].data["message"]


class TestWebSocketConsoleIntegration:
    """Test integration between console and WebSocket."""

    def test_console_websocket_connection(self, config, session_id):
        """Test console initializing WebSocket."""
        from src.console.cli import DevMatrixConsole

        console = DevMatrixConsole(config)
        console.session_id = session_id

        # Should be able to create client
        ws_client = WebSocketClient(config.websocket_url, session_id)
        assert ws_client.session_id == session_id

    def test_console_receives_pipeline_updates(self, session_id):
        """Test console receiving and handling pipeline updates."""
        from src.console.websocket_client import WebSocketClient, PipelineUpdate

        client = WebSocketClient("ws://localhost:8000", session_id)

        # Track received updates
        received_updates = []

        def handle_update(update):
            received_updates.append(update)

        client.subscribe("pipeline_update", handle_update)

        # Simulate backend update
        update = PipelineUpdate(
            type="progress_update",
            timestamp="2025-11-16T14:31:00",
            data={
                "total_tasks": 10,
                "completed_tasks": 7,
                "current_task": "Running integration tests",
            },
        )

        client._emit_callback("pipeline_update", update)

        assert len(received_updates) == 1
        assert received_updates[0].data["completed_tasks"] == 7

    def test_console_error_recovery(self, session_id):
        """Test error event triggers recovery options."""
        from src.console.websocket_client import WebSocketClient, PipelineUpdate

        client = WebSocketClient("ws://localhost:8000", session_id)

        error_events = []

        def handle_error(update):
            error_events.append(update)

        client.subscribe("error", handle_error)

        # Simulate error
        update = PipelineUpdate(
            type="error",
            timestamp="2025-11-16T14:31:15",
            data={
                "message": "Task failed: Connection timeout",
                "recoverable": True,
                "suggested_action": "retry",
            },
        )

        client._emit_callback("error", update)

        assert len(error_events) == 1
        assert error_events[0].data["recoverable"] is True


# Test markers for optional real integration
pytestmark = pytest.mark.integration
