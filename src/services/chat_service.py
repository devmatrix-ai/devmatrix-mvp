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
from src.agents.agent_registry import AgentRegistry, AgentCapability
from src.agents.implementation_agent import ImplementationAgent
from src.agents.testing_agent import TestingAgent
from src.agents.documentation_agent import DocumentationAgent
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
        from src.llm.anthropic_client import AnthropicClient

        self.logger = StructuredLogger("chat_service")
        self.conversations: Dict[str, Conversation] = {}
        self.registry = AgentRegistry()
        self.progress_callback = None  # Will be set per-request for WebSocket streaming

        # Register specialized agents
        self._register_agents()

        # Orchestrator will be created per-request to use specific progress callback
        self.api_key = api_key

        # Create shared LLM client for conversational mode
        self.llm = AnthropicClient(api_key=api_key)

    def _register_agents(self):
        """Register all specialized agents in the registry."""
        # Implementation Agent
        self.registry.register(
            name="ImplementationAgent",
            agent_class=ImplementationAgent,
            capabilities={
                AgentCapability.CODE_GENERATION,
                AgentCapability.API_DESIGN,
                AgentCapability.REFACTORING
            },
            priority=10,
            description="Python code generation and implementation"
        )

        # Testing Agent
        self.registry.register(
            name="TestingAgent",
            agent_class=TestingAgent,
            capabilities={
                AgentCapability.UNIT_TESTING,
                AgentCapability.INTEGRATION_TESTING
            },
            priority=8,
            description="Test generation and execution"
        )

        # Documentation Agent
        self.registry.register(
            name="DocumentationAgent",
            agent_class=DocumentationAgent,
            capabilities={
                AgentCapability.API_DOCUMENTATION,
                AgentCapability.CODE_DOCUMENTATION,
                AgentCapability.USER_DOCUMENTATION
            },
            priority=6,
            description="Documentation generation"
        )

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
        # Detect if this is a direct implementation request or a discussion
        message_lower = message.lower().strip()

        # Keywords that indicate the user wants immediate implementation
        implementation_keywords = ['crear', 'create', 'generar', 'generate', 'implementar', 'implement',
                                  'hacer', 'make', 'escribir', 'write', 'code', 'coder', 'programa',
                                  'desarrollar', 'develop', 'armar', 'build']

        # Keywords indicating user gave enough context and is ready
        ready_keywords = ['si a todo', 'yes to all', 'dale arran', 'empecemos', "let's start",
                         'vamos', "let's go", 'dale', 'ok listo']

        # Keywords for planning/discussion (when user is asking questions)
        discussion_keywords = ['diseñar', 'design', 'planear', 'plan', 'pensar', 'think',
                              'podria', 'podría', 'como', 'cómo', 'que te parece', 'qué te parece']

        # Check conversation history - if user already gave detailed specs, they're ready
        recent_messages = conversation.get_history(limit=5)
        user_gave_details = len([m for m in recent_messages if m['role'] == 'user']) >= 3

        # Check message length - detailed messages with tech specs = ready
        word_count = len(message.split())
        has_tech_details = any(tech in message_lower for tech in
                              ['api', 'backend', 'frontend', 'database', 'db', 'fastapi', 'django',
                               'react', 'vue', 'angular', 'postgres', 'mongodb', 'redis', 'sprint',
                               'kanban', 'jira', 'git', 'docker', 'kubernetes'])

        is_detailed_request = word_count > 30 and has_tech_details

        # Check if it's a direct implementation request or user is ready
        is_direct_implementation = (
            (any(keyword in message_lower for keyword in implementation_keywords) and
             not any(keyword in message_lower for keyword in discussion_keywords)) or
            any(keyword in message_lower for keyword in ready_keywords) or
            is_detailed_request or
            (user_gave_details and word_count > 20)  # After 3+ messages with detail, assume ready
        )

        if is_direct_implementation:
            # Direct implementation - go straight to orchestration
            async for chunk in self._execute_orchestration(conversation, message):
                yield chunk
        else:
            # Conversational mode - discuss and help user refine the idea
            async for chunk in self._handle_conversational(conversation, message):
                yield chunk

    async def _handle_conversational(
        self,
        conversation: Conversation,
        message: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Handle conversational messages - greetings, questions, design discussions."""
        try:
            # Use LLM for friendly conversation
            loop = asyncio.get_event_loop()

            # Get conversation history for context
            recent_messages = conversation.get_history(limit=10)
            history_context = "\n".join([
                f"{msg['role']}: {msg['content'][:200]}"  # Limit each message to 200 chars
                for msg in recent_messages[-5:]  # Last 5 messages
            ])

            system_prompt = """Sos un asistente de IA amigable y conversacional llamado DevMatrix, especializado en desarrollo de software.

Características:
- Hablás en español argentino de manera natural y relajada
- Sos útil y profesional pero no formal ni robótico
- Cuando el usuario te saluda, saludás de vuelta y le contás brevemente qué podés hacer
- Si el usuario quiere diseñar/planear algo, ayudalo a definir los requerimientos pero NO seas insistente
- Hacé máximo 2-3 preguntas de clarificación por respuesta, no más
- Si el usuario ya dio suficiente contexto (menciona tecnologías, features, roles, etc.), decile que ya tenés todo y que use "crear" o "implementar" para empezar
- Si te preguntan sobre tecnologías o arquitectura, dales tu opinión directamente
- Mantené las respuestas cortas (2-4 oraciones)
- Usá formato markdown solo cuando ayude a la claridad
- Si detectás que el usuario está listo (dio detalles técnicos, respondió a tus preguntas), no sigas preguntando - decile cómo activar la implementación

Tus capacidades:
- Conversar sobre diseño de software y arquitectura
- Ayudar a definir requerimientos (pero no seas pesado con las preguntas)
- Responder preguntas técnicas directamente
- Cuando el usuario esté listo, decile que use "crear X" o "implementar Y" para que orqueste

Ejemplos de interacción:
- Usuario: "podríamos diseñar una app de task manager con FastAPI?" → "¡Dale! Task manager con FastAPI suena bien. ¿Qué features principales necesitás? (autenticación, asignación de tareas, notificaciones, etc.)"
- Usuario: "necesito kanban, sprints, roles Dev/PO/Lead" → "Perfecto, ya tengo claro el scope. Cuando quieras arrancar con la implementación, decime 'crear task manager con FastAPI, kanban, sprints y roles' y lo orquesto."
- Usuario: "qué me recomendás para una API?" → "Depende del caso de uso. FastAPI es genial para APIs modernas y rápidas, Django REST si necesitás muchas features out-of-the-box, Flask si preferís minimalismo. ¿Qué tipo de proyecto es?"""

            user_prompt = f"""Conversación reciente:
{history_context}

Usuario: {message}

Respondé de manera natural, amigable y útil. Si es una pregunta de diseño o planificación, hacé preguntas para entender mejor lo que necesita."""

            response = await loop.run_in_executor(
                None,
                lambda: self.llm.generate(
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt,
                    temperature=0.7,
                    max_tokens=400
                )
            )

            content = response['content']

            # Add assistant response to conversation
            assistant_message = Message(
                content=content,
                role=MessageRole.ASSISTANT,
            )
            conversation.add_message(assistant_message)

            # Yield response
            yield {
                "type": "message",
                "role": MessageRole.ASSISTANT.value,
                "content": content,
                "done": True,
            }

        except Exception as e:
            error_message = f"Error en conversación: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            yield {
                "type": "error",
                "content": error_message,
                "done": True,
            }

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
                "content": "Iniciando orquestación...",
                "done": False,
            }

            # Create a queue for progress events
            progress_queue = asyncio.Queue()

            # Create progress callback that puts events in queue
            def progress_callback(event_type: str, data: dict):
                """Callback to capture progress events from orchestrator."""
                try:
                    # Put event in queue (non-blocking)
                    asyncio.create_task(progress_queue.put({
                        "event_type": event_type,
                        "data": data
                    }))
                except Exception as e:
                    self.logger.error(f"Error in progress callback: {e}")

            # Create orchestrator with progress callback
            orchestrator = OrchestratorAgent(
                api_key=self.api_key,
                agent_registry=self.registry,
                progress_callback=progress_callback
            )

            # Execute orchestration in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            # Start orchestration task
            orchestration_task = loop.run_in_executor(
                None,
                orchestrator.orchestrate,
                request,
                conversation.workspace_id,
                None,
            )

            # Stream progress events while orchestration runs
            result = None
            while True:
                try:
                    # Wait for either a progress event or orchestration completion
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(progress_queue.get()),
                            asyncio.create_task(orchestration_task)
                        ],
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=0.1
                    )

                    for task in done:
                        if task == orchestration_task or (hasattr(task, '_coro') and 'orchestrate' in str(task._coro)):
                            # Orchestration completed
                            result = await task
                            break
                        else:
                            # Progress event received
                            event = await task
                            yield {
                                "type": "progress",
                                "event": event["event_type"],
                                "data": event["data"],
                                "done": False,
                            }

                    if result is not None:
                        break

                except asyncio.TimeoutError:
                    continue

            # Drain any remaining progress events
            while not progress_queue.empty():
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                    yield {
                        "type": "progress",
                        "event": event["event_type"],
                        "data": event["data"],
                        "done": False,
                    }
                except asyncio.TimeoutError:
                    break

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
