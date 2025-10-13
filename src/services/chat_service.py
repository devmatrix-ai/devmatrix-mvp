"""
Chat Service

Manages conversational interactions with agents, supporting commands,
context management, and streaming responses.
"""

import uuid
import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime
from enum import Enum

from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.agent_registry import AgentRegistry
from src.observability import StructuredLogger


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message:
    """Chat message model."""

    def __init__(
        self,
        content: str,
        role: MessageRole = MessageRole.USER,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.content = content
        self.role = role
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "content": self.content,
            "role": self.role.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class Conversation:
    """Conversation container with message history."""

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.workspace_id = workspace_id
        self.messages: List[Message] = []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_message(self, message: Message) -> None:
        """Add message to conversation."""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history."""
        messages = self.messages[-limit:] if limit else self.messages
        return [msg.to_dict() for msg in messages]

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "workspace_id": self.workspace_id,
            "messages": self.get_history(),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ChatCommand:
    """Chat command parser and executor."""

    COMMANDS = {
        "/orchestrate": "Orchestrate multi-agent workflow",
        "/analyze": "Analyze project or code",
        "/test": "Run tests",
        "/help": "Show available commands",
        "/clear": "Clear conversation history",
        "/workspace": "Show current workspace info",
    }

    @classmethod
    def is_command(cls, message: str) -> bool:
        """Check if message is a command."""
        return message.strip().startswith("/")

    @classmethod
    def parse_command(cls, message: str) -> tuple[str, str]:
        """
        Parse command and arguments.

        Returns:
            tuple: (command, args)
        """
        parts = message.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return command, args

    @classmethod
    def get_help(cls) -> str:
        """Get help text for all commands."""
        lines = ["Available commands:"]
        for cmd, desc in cls.COMMANDS.items():
            lines.append(f"  {cmd}: {desc}")
        return "\n".join(lines)


class ChatService:
    """
    Chat service for conversational agent interaction.

    Manages conversations, message history, command execution,
    and streaming responses from agents.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize chat service.

        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        self.logger = StructuredLogger("chat_service")
        self.conversations: Dict[str, Conversation] = {}
        self.registry = AgentRegistry()
        self.orchestrator = OrchestratorAgent(api_key=api_key, agent_registry=self.registry)

    def create_conversation(
        self,
        workspace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create new conversation.

        Args:
            workspace_id: Associated workspace ID
            metadata: Additional conversation metadata

        Returns:
            Conversation ID
        """
        conversation = Conversation(
            workspace_id=workspace_id,
            metadata=metadata,
        )
        self.conversations[conversation.conversation_id] = conversation

        self.logger.info(
            f"Created conversation {conversation.conversation_id}",
            extra={"workspace_id": workspace_id}
        )

        return conversation.conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete conversation.

        Returns:
            True if deleted, False if not found
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            self.logger.info(f"Deleted conversation {conversation_id}")
            return True
        return False

    def list_conversations(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all conversations, optionally filtered by workspace.

        Args:
            workspace_id: Filter by workspace ID

        Returns:
            List of conversation dictionaries
        """
        conversations = self.conversations.values()

        if workspace_id:
            conversations = [c for c in conversations if c.workspace_id == workspace_id]

        return [c.to_dict() for c in conversations]

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send message and get streaming response.

        Args:
            conversation_id: Conversation ID
            content: User message content
            metadata: Additional message metadata

        Yields:
            Response chunks with role, content, and metadata

        Raises:
            ValueError: If conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Add user message
        user_message = Message(
            content=content,
            role=MessageRole.USER,
            metadata=metadata,
        )
        conversation.add_message(user_message)

        self.logger.info(
            f"Processing message in conversation {conversation_id}",
            extra={"message_length": len(content)}
        )

        # Check if message is a command
        if ChatCommand.is_command(content):
            async for chunk in self._handle_command(conversation, content):
                yield chunk
        else:
            async for chunk in self._handle_regular_message(conversation, content):
                yield chunk

    async def _handle_command(
        self,
        conversation: Conversation,
        message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle command execution."""
        command, args = ChatCommand.parse_command(message)

        if command == "/help":
            response = ChatCommand.get_help()
            yield {
                "type": "message",
                "role": MessageRole.SYSTEM.value,
                "content": response,
                "done": True,
            }

            system_message = Message(
                content=response,
                role=MessageRole.SYSTEM,
            )
            conversation.add_message(system_message)

        elif command == "/clear":
            conversation.messages.clear()
            yield {
                "type": "message",
                "role": MessageRole.SYSTEM.value,
                "content": "Conversation cleared.",
                "done": True,
            }

        elif command == "/workspace":
            workspace_info = {
                "workspace_id": conversation.workspace_id,
                "conversation_id": conversation.conversation_id,
                "message_count": len(conversation.messages),
            }
            response = f"Workspace Info:\n```json\n{workspace_info}\n```"
            yield {
                "type": "message",
                "role": MessageRole.SYSTEM.value,
                "content": response,
                "done": True,
            }

        elif command == "/orchestrate":
            if not args:
                yield {
                    "type": "error",
                    "content": "Usage: /orchestrate <project description>",
                    "done": True,
                }
                return

            # Execute orchestration
            async for chunk in self._execute_orchestration(conversation, args):
                yield chunk

        else:
            yield {
                "type": "error",
                "content": f"Unknown command: {command}. Type /help for available commands.",
                "done": True,
            }

    async def _handle_regular_message(
        self,
        conversation: Conversation,
        message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle regular conversation message."""
        # For now, treat regular messages as orchestration requests
        # In the future, this could route to different agents based on context
        async for chunk in self._execute_orchestration(conversation, message):
            yield chunk

    async def _execute_orchestration(
        self,
        conversation: Conversation,
        request: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute orchestration and stream progress.

        Yields:
            Progress updates and final result
        """
        try:
            # Send initial status
            yield {
                "type": "status",
                "content": "Starting orchestration...",
                "done": False,
            }

            # Execute orchestration in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.orchestrator.orchestrate,
                request,
                conversation.workspace_id,
                None,
            )

            # Format result as message
            response_lines = [
                f"## Orchestration Complete",
                f"",
                f"**Workspace**: `{result['workspace_id']}`",
                f"**Project Type**: {result['project_type']}",
                f"**Complexity**: {result['complexity']:.1f}",
                f"**Tasks**: {len(result['tasks'])}",
                f"",
                f"### Task Breakdown:",
            ]

            for task in result['tasks']:
                deps = f" (depends on: {', '.join(task['dependencies'])})" if task['dependencies'] else ""
                response_lines.append(
                    f"- **{task['id']}**: {task['description']}{deps}"
                )

            response = "\n".join(response_lines)

            # Add assistant response to conversation
            assistant_message = Message(
                content=response,
                role=MessageRole.ASSISTANT,
                metadata={"orchestration_result": result},
            )
            conversation.add_message(assistant_message)

            # Yield final response
            yield {
                "type": "message",
                "role": MessageRole.ASSISTANT.value,
                "content": response,
                "metadata": result,
                "done": True,
            }

        except Exception as e:
            error_message = f"Error during orchestration: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            yield {
                "type": "error",
                "content": error_message,
                "done": True,
            }
